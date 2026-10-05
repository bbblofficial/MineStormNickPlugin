package com.yourname.nick.skin;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.yourname.nick.NickPlugin;
import com.yourname.nick.model.SkinData;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.util.Async;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.BiConsumer;
import org.bukkit.configuration.file.FileConfiguration;

public final class SkinCacheManager {

    private static final String PROFILE_URL = "https://api.mojang.com/users/profiles/minecraft/";
    private static final String SESSION_URL = "https://sessionserver.mojang.com/session/minecraft/profile/";

    private static final class CachedSkin {
        final String name;
        final String value;
        final String signature;
        final long fetchedAt;

        CachedSkin(String name, String value, String signature, long fetchedAt) {
            this.name = name;
            this.value = value;
            this.signature = signature;
            this.fetchedAt = fetchedAt;
        }

        SkinData toSkinData(String labelPrefix) {
            return SkinData.custom(this.value, this.signature, labelPrefix + this.name);
        }
    }

    private final NickPlugin plugin;
    private final long ttlMillis;
    private final int  timeoutMillis;
    private final Path cacheDirectory;

    private final ConcurrentMap<String, CachedSkin> memory   = new ConcurrentHashMap<String, CachedSkin>();
    private final ConcurrentMap<String, CompletableFuture<Optional<SkinData>>> inflight =
            new ConcurrentHashMap<String, CompletableFuture<Optional<SkinData>>>();
    private final List<SkinData> pool = new CopyOnWriteArrayList<SkinData>();

    public SkinCacheManager(NickPlugin plugin) {
        this.plugin = plugin;
        FileConfiguration cfg = plugin.getConfig();
        this.ttlMillis = Math.max(1L, cfg.getLong("skins.cache-ttl-minutes", 1440L)) * 60000L;
        this.timeoutMillis = (int) Math.max(2000L,
                cfg.getLong("skins.request-timeout-seconds", 10L) * 1000L);
        this.cacheDirectory = plugin.getDataFolder().toPath().resolve("skincache");
    }

    public void initialize() {
        FileConfiguration cfg = this.plugin.getConfig();

        for (Map<?, ?> entry : cfg.getMapList("skins.pool")) {
            Object value = entry.get("value");
            Object signature = entry.get("signature");
            Object label = entry.get("label");
            if (value == null || signature == null) {
                this.plugin.getLogger().warning(
                        "Ignoring skins.pool entry without value and signature.");
                continue;
            }
            String name = (label == null)
                    ? ("custom" + (this.pool.size() + 1))
                    : String.valueOf(label);
            this.pool.add(SkinData.custom(
                    String.valueOf(value), String.valueOf(signature), "POOL:" + name));
        }

        final List<String> names = cfg.getStringList("skins.pool-players");
        if (!names.isEmpty()) {
            Async.supply(this.plugin, new Async.ThrowingSupplier<Integer>() {
                @Override
                public Integer get() {
                    int loaded = 0;
                    for (String name : names) {
                        if (!NameValidator.isValidFormat(name)) {
                            plugin.getLogger().warning(
                                    "Ignoring invalid skins.pool-players entry '" + name + "'.");
                            continue;
                        }
                        try {
                            Optional<CachedSkin> skin = resolve(name);
                            if (skin.isPresent()) {
                                pool.add(skin.get().toSkinData("POOL:"));
                                loaded++;
                            } else {
                                plugin.getLogger().warning(
                                        "No skin found for pool player '" + name + "'.");
                            }
                        } catch (IOException e) {
                            plugin.getLogger().warning(
                                    "Could not load pool skin '" + name + "': " + e.getMessage());
                        }
                    }
                    return Integer.valueOf(loaded);
                }
            });
        }
        if (this.pool.isEmpty() && names.isEmpty()) {
            this.plugin.getLogger().warning(
                    "The random skin pool is empty; players choosing 'Random skin' will get "
                            + "the Steve/Alex skin.");
        }
    }

    public CompletableFuture<Optional<SkinData>> fetchByName(final String name) {
        if (!NameValidator.isValidFormat(name)) {
            return CompletableFuture.completedFuture(Optional.<SkinData>empty());
        }
        final String key = name.toLowerCase(Locale.ROOT);
        CompletableFuture<Optional<SkinData>> existing = this.inflight.get(key);
        if (existing != null) {
            return existing;
        }
        CompletableFuture<Optional<SkinData>> created =
                Async.supply(this.plugin, new Async.ThrowingSupplier<Optional<SkinData>>() {
                    @Override
                    public Optional<SkinData> get() throws Exception {
                        Optional<CachedSkin> skin = resolve(name);
                        if (skin.isPresent()) {
                            return Optional.of(skin.get().toSkinData("PLAYER:"));
                        }
                        return Optional.empty();
                    }
                });
        this.inflight.put(key, created);
        created.whenComplete(new BiConsumer<Optional<SkinData>, Throwable>() {
            @Override
            public void accept(Optional<SkinData> data, Throwable error) {
                inflight.remove(key);
            }
        });
        return created;
    }

    public Optional<SkinData> randomPoolSkin() {
        List<SkinData> snapshot = new ArrayList<SkinData>(this.pool);
        if (snapshot.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(snapshot.get(
                ThreadLocalRandom.current().nextInt(snapshot.size())));
    }

    public int poolSize() {
        return this.pool.size();
    }

    public void shutdown() {
        this.memory.clear();
        this.inflight.clear();
        this.pool.clear();
    }

    private Optional<CachedSkin> resolve(String name) throws IOException {
        String key = name.toLowerCase(Locale.ROOT);
        CachedSkin cached = this.memory.get(key);
        if (cached == null) {
            cached = readDisk(key);
            if (cached != null) {
                this.memory.put(key, cached);
            }
        }
        if (cached != null && System.currentTimeMillis() - cached.fetchedAt < this.ttlMillis) {
            return Optional.of(cached);
        }
        Optional<CachedSkin> fresh = download(name);
        if (fresh.isPresent()) {
            this.memory.put(key, fresh.get());
            writeDisk(key, fresh.get());
        }
        return fresh;
    }

    private Optional<CachedSkin> download(String name) throws IOException {
        String lookupBody = get(PROFILE_URL + name);
        if (lookupBody == null) {
            return Optional.empty();
        }
        try {
            JsonObject identity = new JsonParser().parse(lookupBody).getAsJsonObject();
            String id = identity.get("id").getAsString();
            String canonicalName = identity.get("name").getAsString();

            String sessionBody = get(SESSION_URL + id + "?unsigned=false");
            if (sessionBody == null) {
                throw new IOException("Mojang session lookup failed");
            }
            JsonArray properties = new JsonParser()
                    .parse(sessionBody).getAsJsonObject().getAsJsonArray("properties");
            for (JsonElement element : properties) {
                JsonObject property = element.getAsJsonObject();
                if ("textures".equals(property.get("name").getAsString())) {
                    String value = property.get("value").getAsString();
                    String signature = property.has("signature")
                            ? property.get("signature").getAsString() : "";
                    return Optional.of(new CachedSkin(
                            canonicalName, value, signature, System.currentTimeMillis()));
                }
            }
            return Optional.empty();
        } catch (RuntimeException e) {
            throw new IOException("Unexpected Mojang response", e);
        }
    }

    private String get(String url) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(this.timeoutMillis);
        connection.setReadTimeout(this.timeoutMillis);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("User-Agent", "NickSystem");
        try {
            int status = connection.getResponseCode();
            if (status == 404 || status == 204) {
                return null;
            }
            if (status != 200) {
                throw new IOException("HTTP " + status + " from " + url);
            }
            StringBuilder sb = new StringBuilder();
            BufferedReader reader = new BufferedReader(new InputStreamReader(
                    connection.getInputStream(), StandardCharsets.UTF_8));
            try {
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line);
                }
            } finally {
                reader.close();
            }
            return sb.toString();
        } finally {
            connection.disconnect();
        }
    }

    private CachedSkin readDisk(String key) {
        Path file = this.cacheDirectory.resolve(key + ".json");
        if (!Files.isRegularFile(file)) {
            return null;
        }
        try {
            String content = new String(Files.readAllBytes(file), StandardCharsets.UTF_8);
            JsonObject object = new JsonParser().parse(content).getAsJsonObject();
            return new CachedSkin(
                    object.get("name").getAsString(),
                    object.get("value").getAsString(),
                    object.get("signature").getAsString(),
                    object.get("fetchedAt").getAsLong());
        } catch (IOException e) {
            this.plugin.getLogger().warning(
                    "Ignoring unreadable skin cache " + file.getFileName() + ": " + e.getMessage());
            return null;
        } catch (RuntimeException e) {
            this.plugin.getLogger().warning(
                    "Ignoring unreadable skin cache " + file.getFileName() + ": " + e.getMessage());
            return null;
        }
    }

    private void writeDisk(String key, CachedSkin skin) {
        JsonObject object = new JsonObject();
        object.addProperty("name", skin.name);
        object.addProperty("value", skin.value);
        object.addProperty("signature", skin.signature);
        object.addProperty("fetchedAt", Long.valueOf(skin.fetchedAt));
        try {
            Files.createDirectories(this.cacheDirectory);
            Files.write(this.cacheDirectory.resolve(key + ".json"),
                    object.toString().getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            this.plugin.getLogger().warning(
                    "Could not write skin cache for " + key + ": " + e.getMessage());
        }
    }
}
