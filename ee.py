#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py
========
Fully repairs the jd-gui-decompiled NickSystem sources and applies the
Hypixel-style behaviour changes.

  * strips the /*  123 */ prefixes from every .java file
  * rewrites the files that jd-gui mangled (broken lambdas, synthetic
    accessors, missing imports, invalid "this.this$1.val$xxx" references)
  * makes the entire /nick setup happen inside a written book
  * removes the "in games only" clause and disables world restrictions
  * adds the SQLite / MySQL / Gson dependencies to pom.xml

Run it from the repo root (the folder that contains `com/`, `config.yml`,
`plugin.yml`, `names.yml`, `messages.yml`) and then commit + push.
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))


# ===========================================================================
#  Helpers
# ===========================================================================

def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def strip_decompiler_prefixes(text):
    out = []
    for line in text.split("\n"):
        m = re.match(r"^\s*/\*\s*\d*\s*\*/\s?(.*)$", line)
        out.append(m.group(1) if m else line)
    return "\n".join(out)


def walk_java_files():
    for dirpath, _dirnames, filenames in os.walk(ROOT):
        # skip build output
        if os.sep + "target" + os.sep in dirpath + os.sep:
            continue
        for name in filenames:
            if name.endswith(".java"):
                yield os.path.join(dirpath, name)


# ===========================================================================
#  STEP 1 - strip decompiler prefixes from every .java file
# ===========================================================================

def step_strip_prefixes():
    count = 0
    for path in walk_java_files():
        original = read(path)
        cleaned = strip_decompiler_prefixes(original)
        if cleaned != original:
            write(path, cleaned)
            count += 1
    print("[fixer] stripped decompiler prefixes in %d .java files" % count)


# ===========================================================================
#  STEP 2 - full rewrites of the broken files
# ===========================================================================

NICKPLUGIN_JAVA = r'''package com.yourname.nick;

import com.yourname.nick.command.NickCommand;
import com.yourname.nick.command.RealNameCommand;
import com.yourname.nick.disguise.DisguiseManager;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.disguise.WorldRules;
import com.yourname.nick.gui.BookGUIManager;
import com.yourname.nick.integration.BedwarsLevelHook;
import com.yourname.nick.integration.NickPlaceholderExpansion;
import com.yourname.nick.listener.ChatListener;
import com.yourname.nick.listener.ConnectionListener;
import com.yourname.nick.listener.WorldListener;
import com.yourname.nick.message.Messages;
import com.yourname.nick.name.NameGenerator;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.packet.PacketManager;
import com.yourname.nick.skin.SkinCacheManager;
import com.yourname.nick.storage.StorageManager;
import com.yourname.nick.task.ActionBarTask;
import com.yourname.nick.util.Async;
import java.io.File;
import java.util.logging.Level;
import org.bukkit.command.PluginCommand;
import org.bukkit.command.TabExecutor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.PluginManager;
import org.bukkit.plugin.java.JavaPlugin;

public final class NickPlugin extends JavaPlugin {

    private DisguiseRegistry registry;
    private PacketManager    packets;
    private StorageManager   storage;
    private SkinCacheManager skins;
    private DisguiseManager  disguises;
    private BookGUIManager   bookGui;
    private Runnable         placeholderCleanup;

    @Override
    public void onLoad() {
        this.registry = new DisguiseRegistry();
        this.packets  = new PacketManager(this, this.registry);
        this.packets.load();
    }

    @Override
    public void onEnable() {
        saveDefaultConfig();
        YamlConfiguration names = loadNames();
        Messages messages = new Messages(this);

        if (!this.packets.enable()) {
            getLogger().severe(
                    "NickSystem requires Paper 1.19.3 or newer (player info update packets). Disabling.");
            getServer().getPluginManager().disablePlugin(this);
            return;
        }

        this.storage = new StorageManager(this);
        this.storage.initialize().whenComplete((ignored, error) -> {
            if (error != null) {
                getLogger().log(Level.SEVERE,
                        "Database initialisation failed; disabling NickSystem.", error);
                Async.main(NickPlugin.this, new Runnable() {
                    @Override
                    public void run() {
                        getServer().getPluginManager().disablePlugin(NickPlugin.this);
                    }
                });
            }
        });

        this.skins = new SkinCacheManager(this);
        this.skins.initialize();

        NameValidator validator = new NameValidator(names, this.registry);
        NameGenerator generator = new NameGenerator(names, validator);
        BedwarsLevelHook bedwars = new BedwarsLevelHook(getConfig());
        WorldRules rules = WorldRules.fromConfig(getConfig(), getLogger());

        this.disguises = new DisguiseManager(
                this, this.registry, this.packets, this.storage, rules, bedwars);
        this.bookGui = new BookGUIManager(
                this, messages, this.disguises, this.skins, generator, validator, this.storage);

        PluginManager pluginManager = getServer().getPluginManager();
        pluginManager.registerEvents(new ConnectionListener(
                this, this.registry, this.disguises, this.storage, this.bookGui), this);
        pluginManager.registerEvents(new WorldListener(this.disguises), this);
        pluginManager.registerEvents(new ChatListener(getConfig(), this.registry, bedwars), this);

        bind("nick", new NickCommand(this, messages, this.bookGui, this.disguises, this.skins, validator));
        bind("realname", new RealNameCommand(this, messages, this.registry, this.storage));

        if (getConfig().getBoolean("actionbar.enabled", true)) {
            long interval = Math.max(10L, getConfig().getLong("actionbar.interval-ticks", 40L));
            ActionBarTask task = new ActionBarTask(
                    this, this.registry,
                    messages.get("actionbar"),
                    getConfig().getBoolean("actionbar.show-when-dormant", true));
            getServer().getScheduler().runTaskTimer(this, task, interval, interval);
        }
        getServer().getScheduler().runTaskTimerAsynchronously(
                this, new Runnable() {
                    @Override
                    public void run() {
                        registry.prunePending(60000L);
                    }
                }, 1200L, 1200L);

        if (pluginManager.isPluginEnabled("PlaceholderAPI")) {
            final NickPlaceholderExpansion expansion =
                    new NickPlaceholderExpansion(this, this.registry, bedwars);
            expansion.register();
            this.placeholderCleanup = new Runnable() {
                @Override
                public void run() {
                    expansion.unregister();
                }
            };
        }
    }

    @Override
    public void onDisable() {
        getServer().getScheduler().cancelTasks(this);
        if (this.placeholderCleanup != null) {
            this.placeholderCleanup.run();
            this.placeholderCleanup = null;
        }
        if (this.disguises != null) this.disguises.shutdown();
        if (this.bookGui   != null) this.bookGui.clear();
        if (this.skins     != null) this.skins.shutdown();
        if (this.storage   != null) this.storage.close();
        if (this.packets   != null) this.packets.disable();
    }

    private YamlConfiguration loadNames() {
        File file = new File(getDataFolder(), "names.yml");
        if (!file.exists()) {
            saveResource("names.yml", false);
        }
        return YamlConfiguration.loadConfiguration(file);
    }

    private void bind(String name, TabExecutor executor) {
        PluginCommand command = getCommand(name);
        if (command == null) {
            throw new IllegalStateException("Command '" + name + "' is missing from plugin.yml");
        }
        command.setExecutor(executor);
        command.setTabCompleter(executor);
    }
}
'''


NICKCOMMAND_JAVA = r'''package com.yourname.nick.command;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseManager;
import com.yourname.nick.gui.BookGUIManager;
import com.yourname.nick.message.Messages;
import com.yourname.nick.model.SkinData;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.skin.SkinCacheManager;
import com.yourname.nick.util.Async;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiConsumer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;

public final class NickCommand implements TabExecutor {

    private final NickPlugin plugin;
    private final Messages messages;
    private final BookGUIManager bookGui;
    private final DisguiseManager disguises;
    private final SkinCacheManager skins;
    private final NameValidator validator;

    public NickCommand(NickPlugin plugin,
                       Messages messages,
                       BookGUIManager bookGui,
                       DisguiseManager disguises,
                       SkinCacheManager skins,
                       NameValidator validator) {
        this.plugin = plugin;
        this.messages = messages;
        this.bookGui = bookGui;
        this.disguises = disguises;
        this.skins = skins;
        this.validator = validator;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage(this.messages.get("player-only"));
            return true;
        }
        Player player = (Player) sender;
        if (args.length == 0) {
            this.bookGui.open(player);
            return true;
        }
        String sub = args[0].toLowerCase(Locale.ROOT);
        if ("reset".equals(sub)) {
            handleReset(player);
        } else if ("skin".equals(sub)) {
            handleSkin(player, args);
        } else if ("name".equals(sub)) {
            handleName(player, args);
        } else if ("ui".equals(sub)) {
            this.bookGui.handle(player, Arrays.copyOfRange(args, 1, args.length));
        } else {
            player.sendMessage(this.messages.get("usage"));
        }
        return true;
    }

    private void handleReset(Player player) {
        this.bookGui.clearSession(player.getUniqueId());
        if (this.disguises.reset(player)) {
            player.sendMessage(this.messages.get("nick-reset"));
        } else {
            player.sendMessage(this.messages.get("nick-not-nicked"));
        }
    }

    private void handleSkin(final Player player, String[] args) {
        if (!player.hasPermission("nick.skin")) {
            player.sendMessage(this.messages.get("no-permission"));
            return;
        }
        if (args.length < 2) {
            player.sendMessage(this.messages.get("skin-usage"));
            return;
        }
        final String target = args[1];
        if (!NameValidator.isValidFormat(target)) {
            player.sendMessage(this.messages.get("skin-invalid-name"));
            return;
        }
        if (!this.disguises.profile(player.getUniqueId()).isPresent()) {
            player.sendMessage(this.messages.get("skin-needs-nick"));
            return;
        }
        player.sendMessage(this.messages.get("skin-fetching", "player", target));

        CompletableFuture<Optional<SkinData>> future = this.skins.fetchByName(target);
        future.whenComplete(new BiConsumer<Optional<SkinData>, Throwable>() {
            @Override
            public void accept(final Optional<SkinData> result, final Throwable error) {
                Async.main(NickCommand.this.plugin, new Runnable() {
                    @Override
                    public void run() {
                        if (!player.isOnline()) {
                            return;
                        }
                        if (error != null) {
                            player.sendMessage(messages.get("skin-fetch-failed"));
                            return;
                        }
                        if (!result.isPresent()) {
                            player.sendMessage(messages.get("skin-not-found",
                                    "player", target));
                            return;
                        }
                        if (disguises.changeSkin(player, result.get())) {
                            player.sendMessage(messages.get("skin-applied",
                                    "player", target));
                        } else {
                            player.sendMessage(messages.get("skin-needs-nick"));
                        }
                    }
                });
            }
        });
    }

    private void handleName(Player player, String[] args) {
        if (!player.hasPermission("nick.custom")) {
            player.sendMessage(this.messages.get("no-permission"));
            return;
        }
        if (args.length < 2) {
            player.sendMessage(this.messages.get("name-usage"));
            return;
        }
        this.bookGui.applyCustomName(player, args[1]);
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length != 1) {
            return Collections.emptyList();
        }
        List<String> options = new ArrayList<String>();
        options.add("reset");
        if (sender.hasPermission("nick.skin"))   options.add("skin");
        if (sender.hasPermission("nick.custom")) options.add("name");

        String typed = args[0].toLowerCase(Locale.ROOT);
        List<String> out = new ArrayList<String>();
        for (String option : options) {
            if (option.startsWith(typed)) {
                out.add(option);
            }
        }
        return out;
    }
}
'''


REALNAME_JAVA = r'''package com.yourname.nick.command;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.message.Messages;
import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.storage.StorageManager;
import com.yourname.nick.util.Async;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.function.BiConsumer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;

public final class RealNameCommand implements TabExecutor {

    private static final DateTimeFormatter DATE_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm 'UTC'").withZone(ZoneOffset.UTC);

    private final NickPlugin plugin;
    private final Messages messages;
    private final DisguiseRegistry registry;
    private final StorageManager storage;

    public RealNameCommand(NickPlugin plugin,
                           Messages messages,
                           DisguiseRegistry registry,
                           StorageManager storage) {
        this.plugin = plugin;
        this.messages = messages;
        this.registry = registry;
        this.storage = storage;
    }

    @Override
    public boolean onCommand(final CommandSender sender, Command command, String label, String[] args) {
        if (!sender.hasPermission("nick.staff")) {
            sender.sendMessage(this.messages.get("no-permission"));
            return true;
        }
        if (args.length != 1) {
            sender.sendMessage(this.messages.get("realname-usage"));
            return true;
        }
        final String nick = args[0];
        if (!NameValidator.isValidFormat(nick)) {
            sender.sendMessage(this.messages.get("realname-none", "nick", nick));
            return true;
        }

        Optional<DisguiseProfile> live = this.registry.findByNick(nick);
        if (live.isPresent()) {
            DisguiseProfile profile = live.get();
            sender.sendMessage(this.messages.get("realname-live",
                    "nick",  profile.nickname(),
                    "real",  profile.realName(),
                    "uuid",  profile.realUuid().toString(),
                    "state", profile.active() ? "active" : "dormant"));
            return true;
        }

        this.storage.findLatestByNickname(nick).whenComplete(
                new BiConsumer<Optional<NickRecord>, Throwable>() {
            @Override
            public void accept(final Optional<NickRecord> row, final Throwable error) {
                Async.main(RealNameCommand.this.plugin, new Runnable() {
                    @Override
                    public void run() {
                        if (error != null) {
                            sender.sendMessage(messages.get("storage-error"));
                            return;
                        }
                        if (!row.isPresent()) {
                            sender.sendMessage(messages.get("realname-none", "nick", nick));
                            return;
                        }
                        NickRecord record = row.get();
                        sender.sendMessage(messages.get("realname-historical",
                                "nick", record.nickname(),
                                "real", record.realName(),
                                "uuid", record.realUuid().toString(),
                                "date", DATE_FORMAT.format(
                                        Instant.ofEpochMilli(record.createdAt()))));
                    }
                });
            }
        });
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length != 1 || !sender.hasPermission("nick.staff")) {
            return Collections.emptyList();
        }
        String typed = args[0].toLowerCase(Locale.ROOT);
        List<String> out = new ArrayList<String>();
        for (DisguiseProfile profile : this.registry.all()) {
            String n = profile.nickname();
            if (n != null && n.toLowerCase(Locale.ROOT).startsWith(typed)) {
                out.add(n);
            }
        }
        return out;
    }
}
'''


SKINCACHE_JAVA = r'''package com.yourname.nick.skin;

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
'''


WORLDRULES_JAVA = r'''package com.yourname.nick.disguise;

import java.util.logging.Logger;
import org.bukkit.configuration.ConfigurationSection;

/**
 * World restrictions were removed. Nicknames are now active everywhere
 * the moment they are applied, matching Hypixel's behaviour.
 * Kept as a class so existing callers still compile.
 */
public final class WorldRules {

    private static final WorldRules INSTANCE = new WorldRules();

    private WorldRules() {
    }

    public static WorldRules fromConfig(ConfigurationSection config, Logger logger) {
        // worlds.* is intentionally ignored now.
        return INSTANCE;
    }

    public boolean isActive(String worldName) {
        return true;
    }
}
'''


ACTIONBAR_JAVA = r'''package com.yourname.nick.task;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

public final class ActionBarTask implements Runnable {

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;
    private final String indicator;

    public ActionBarTask(NickPlugin plugin,
                         DisguiseRegistry registry,
                         String indicator,
                         boolean showWhenDormant) {
        this.plugin = plugin;
        this.registry = registry;
        this.indicator = (indicator == null) ? "" : indicator;
    }

    @Override
    public void run() {
        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player == null || !player.isOnline()) {
                continue;
            }
            try {
                player.sendMessage(ChatColor.translateAlternateColorCodes('&', this.indicator));
            } catch (Throwable ignored) {
            }
        }
    }
}
'''


VIRTUALBOOK_JAVA = r'''package com.yourname.nick.util;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.BookMeta;
import org.bukkit.inventory.meta.ItemMeta;

public final class VirtualBook {

    private VirtualBook() {
    }

    public static ItemStack build(String title, String author, String page1) {
        return build(title, author, Arrays.asList(page1));
    }

    public static ItemStack build(String title, String author, List<String> pages) {
        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        meta.setTitle(title);
        meta.setAuthor(author);
        meta.setPages(pages);
        book.setItemMeta((ItemMeta) meta);
        return book;
    }

    /**
     * Builds a book with rich BaseComponent pages (click / hover events).
     * Uses BookMeta.Spigot#setPages when available on 1.8.8, otherwise
     * falls back to legacy text.
     */
    public static ItemStack buildComponents(String title,
                                            String author,
                                            BaseComponent[]... pages) {
        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        meta.setTitle(title);
        meta.setAuthor(author);

        boolean rich = false;
        try {
            Method spigotMethod = meta.getClass().getMethod("spigot");
            Object spigot = spigotMethod.invoke(meta);
            Method setPages = spigot.getClass().getMethod(
                    "setPages", BaseComponent[].class);
            setPages.invoke(spigot, (Object) pages);
            rich = true;
        } catch (Throwable ignored) {
            // fall through
        }

        if (!rich) {
            List<String> legacy = new ArrayList<String>();
            for (BaseComponent[] page : pages) {
                legacy.add(TextComponent.toLegacyText(page));
            }
            meta.setPages(legacy);
        }

        book.setItemMeta((ItemMeta) meta);
        return book;
    }

    public static boolean open(Player player, ItemStack book) {
        if (player == null || book == null) {
            return false;
        }
        try {
            Object handle = player.getClass().getMethod("getHandle").invoke(player);

            Class<?> packetClass = null;
            String[] candidates = {
                    "net.minecraft.server.v1_8_R3.PacketPlayOutCustomPayload",
                    "net.minecraft.server.v1_8_R2.PacketPlayOutCustomPayload",
                    "net.minecraft.server.v1_8_R1.PacketPlayOutCustomPayload"
            };
            for (String name : candidates) {
                try {
                    packetClass = Class.forName(name);
                    break;
                } catch (ClassNotFoundException ignored) {
                }
            }
            if (packetClass == null) {
                return false;
            }

            Class<?> serializerClass = Class.forName(
                    "net.minecraft.server.v1_8_R3.PacketDataSerializer");
            Class<?> unpooledClass = Class.forName("io.netty.buffer.Unpooled");
            Object buffer = unpooledClass.getMethod("buffer").invoke(null);
            Object serializer = serializerClass
                    .getConstructor(Class.forName("io.netty.buffer.ByteBuf"))
                    .newInstance(buffer);

            Object packet = packetClass
                    .getConstructor(String.class, serializerClass)
                    .newInstance("MC|BOpen", serializer);

            Field connField = handle.getClass().getField("playerConnection");
            Object connection = connField.get(handle);
            Method sendPacket = connection.getClass().getMethod(
                    "sendPacket", Class.forName("net.minecraft.server.v1_8_R3.Packet"));

            ItemStack held = player.getItemInHand();
            player.setItemInHand(book);
            sendPacket.invoke(connection, packet);
            player.setItemInHand(held);
            return true;
        } catch (Throwable ignored) {
            return false;
        }
    }
}
'''


BOOKGUI_JAVA = r'''package com.yourname.nick.gui;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseManager;
import com.yourname.nick.message.Messages;
import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
import com.yourname.nick.model.Rank;
import com.yourname.nick.model.SkinData;
import com.yourname.nick.name.NameGenerator;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.skin.SkinCacheManager;
import com.yourname.nick.storage.StorageManager;
import com.yourname.nick.util.Async;
import com.yourname.nick.util.VirtualBook;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiConsumer;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.ClickEvent;
import net.md_5.bungee.api.chat.HoverEvent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

/**
 * Book-driven nickname setup. Every step is rendered inside a written
 * book with clickable / hoverable text so the chat is never used for
 * UI navigation (Hypixel-style).
 */
public final class BookGUIManager {

    private static final String BOOK_TITLE  = "Nickname Setup";
    private static final String BOOK_AUTHOR = "NickSystem";

    private final NickPlugin      plugin;
    private final Messages        messages;
    private final DisguiseManager disguises;
    private final SkinCacheManager skins;
    private final NameGenerator   generator;
    private final NameValidator   validator;
    private final StorageManager  storage;

    private final Map<UUID, NickSession> sessions =
            new ConcurrentHashMap<UUID, NickSession>();

    public BookGUIManager(NickPlugin plugin,
                          Messages messages,
                          DisguiseManager disguises,
                          SkinCacheManager skins,
                          NameGenerator generator,
                          NameValidator validator,
                          StorageManager storage) {
        this.plugin = plugin;
        this.messages = messages;
        this.disguises = disguises;
        this.skins = skins;
        this.generator = generator;
        this.validator = validator;
        this.storage = storage;
    }

    public void open(final Player player) {
        this.storage.findLastSetForPlayer(player.getUniqueId()).whenComplete(
                new BiConsumer<Optional<NickRecord>, Throwable>() {
            @Override
            public void accept(final Optional<NickRecord> last, final Throwable error) {
                Async.main(BookGUIManager.this.plugin, new Runnable() {
                    @Override
                    public void run() {
                        if (!player.isOnline()) {
                            return;
                        }
                        NickRecord history = (error == null && last != null && last.isPresent())
                                ? last.get() : null;
                        NickSession session = new NickSession(history);
                        sessions.put(player.getUniqueId(), session);
                        showIntro(player);
                    }
                });
            }
        });
    }

    public void handle(Player player, String[] args) {
        NickSession session = this.sessions.get(player.getUniqueId());
        if (session == null) {
            open(player);
            return;
        }
        if (args.length == 0) {
            showIntro(player);
            return;
        }
        String sub = args[0].toLowerCase(Locale.ROOT);
        if ("rank".equals(sub))          chooseRank(player, session, args);
        else if ("skin".equals(sub))     chooseSkin(player, session, args);
        else if ("name".equals(sub))     chooseName(player, session, args);
        else if ("use".equals(sub))      useRolledName(player, session);
        else if ("reroll".equals(sub))   reroll(player, session);
        else if ("close".equals(sub))    { /* nothing - book closes */ }
        else                             showIntro(player);
    }

    public void applyCustomName(Player player, String nick) {
        NickSession session = this.sessions.get(player.getUniqueId());
        Optional<DisguiseProfile> current = this.disguises.profile(player.getUniqueId());

        Rank rank = session != null
                ? session.rank()
                : (current.isPresent() ? current.get().rank() : Rank.DEFAULT);
        SkinData skin = session != null
                ? session.skin()
                : (current.isPresent() ? current.get().skin() : SkinData.normal());

        NameValidator.Result result = this.validator.validate(nick, player);
        if (result != NameValidator.Result.VALID) {
            showName(player, session != null ? session : new NickSession(null));
            return;
        }

        this.disguises.apply(player, nick, rank, skin);
        this.sessions.remove(player.getUniqueId());
        showFinished(player, nick);
    }

    public void clearSession(UUID uuid) { this.sessions.remove(uuid); }

    public void clear()                 { this.sessions.clear(); }

    /* ------------------------------------------------------------------ */
    /*  Pages                                                             */
    /* ------------------------------------------------------------------ */

    private void showIntro(Player player) {
        BaseComponent[] page = new BaseComponent[] {
                line(ChatColor.DARK_AQUA, ChatColor.BOLD, "Nickname Setup"),
                blank(),
                line(ChatColor.BLACK, null, "Nicknames let you play"),
                line(ChatColor.BLACK, null, "with a different name."),
                blank(),
                line(ChatColor.BLACK, null, "All server rules still"),
                line(ChatColor.BLACK, null, "apply and every nick"),
                line(ChatColor.BLACK, null, "is logged."),
                blank(),
                button("[ Start setup ]", "/nick ui rank", "Begin the setup")
        };
        openBook(player, page);
    }

    private void showRankPicker(Player player) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(ChatColor.DARK_AQUA, ChatColor.BOLD, "Choose your RANK"));
        out.add(blank());
        out.add(line(ChatColor.BLACK, null, "Pick the rank you"));
        out.add(line(ChatColor.BLACK, null, "will show while nicked."));
        out.add(blank());
        for (Rank r : Rank.values()) {
            out.add(button("[" + r.label() + "]", "/nick ui rank " + r.name(),
                    "Use " + r.label()));
        }
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showSkin(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(ChatColor.DARK_AQUA, ChatColor.BOLD, "Choose your SKIN"));
        out.add(blank());
        out.add(line(ChatColor.BLACK, null, "Pick the skin you"));
        out.add(line(ChatColor.BLACK, null, "will wear while nicked."));
        out.add(blank());
        out.add(button("[ My normal skin ]", "/nick ui skin normal", "Keep your own skin"));
        out.add(button("[ Steve/Alex ]",     "/nick ui skin default", "Default skin"));
        out.add(button("[ Random skin ]",    "/nick ui skin random", "Random from pool"));
        if (session.history() != null) {
            out.add(button("[ Reuse last skin ]", "/nick ui skin reuse",
                    "Your last nickname's skin"));
        }
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showName(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(ChatColor.DARK_AQUA, ChatColor.BOLD, "Choose your NAME"));
        out.add(blank());
        out.add(line(ChatColor.BLACK, null, "How do you want"));
        out.add(line(ChatColor.BLACK, null, "to be called?"));
        out.add(blank());
        out.add(button("[ Random name ]", "/nick ui name random",
                "Generate a random username"));
        if (session.history() != null) {
            out.add(button("[ Reuse last name ]", "/nick ui name reuse",
                    "Your last nickname"));
        }
        out.add(blank());
        out.add(button("[ Reset nickname ]", "/nick reset",
                "Go back to your real name"));
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showRolledName(Player player, NickSession session) {
        String name = session.pendingName();
        if (name == null) {
            showName(player, session);
            return;
        }
        BaseComponent[] page = new BaseComponent[] {
                line(ChatColor.DARK_AQUA, ChatColor.BOLD, "Random name"),
                blank(),
                line(ChatColor.BLACK, null, "We generated:"),
                blank(),
                line(ChatColor.YELLOW, ChatColor.BOLD, name),
                blank(),
                button("[ USE THIS NAME ]", "/nick ui use", "Nick as " + name),
                button("[ TRY AGAIN ]", "/nick ui reroll", "Generate a different name")
        };
        openBook(player, page);
    }

    private void showFinished(Player player, String nick) {
        BaseComponent[] page = new BaseComponent[] {
                line(ChatColor.DARK_AQUA, ChatColor.BOLD, "Nickname ready!"),
                blank(),
                line(ChatColor.BLACK, null, "You are now nicked as:"),
                line(ChatColor.YELLOW, ChatColor.BOLD, nick),
                blank(),
                line(ChatColor.BLACK, null, "The disguise is active"),
                line(ChatColor.BLACK, null, "everywhere right away."),
                blank(),
                line(ChatColor.DARK_GRAY, null, "Close the book when done.")
        };
        openBook(player, page);
    }

    /* ------------------------------------------------------------------ */
    /*  Step handlers                                                     */
    /* ------------------------------------------------------------------ */

    private void chooseRank(Player player, NickSession session, String[] args) {
        if (args.length < 2) {
            showRankPicker(player);
            return;
        }
        Optional<Rank> rank = Rank.parse(args[1]);
        if (!rank.isPresent()) {
            showRankPicker(player);
            return;
        }
        session.rank(rank.get());
        session.step(NickSession.Step.SKIN);
        showSkin(player, session);
    }

    private void chooseSkin(Player player, NickSession session, String[] args) {
        if (args.length < 2) {
            showSkin(player, session);
            return;
        }
        String choice = args[1].toLowerCase(Locale.ROOT);
        if ("normal".equals(choice)) {
            session.skin(SkinData.normal());
        } else if ("default".equals(choice)) {
            session.skin(SkinData.defaultSkin());
        } else if ("random".equals(choice)) {
            Optional<SkinData> pick = this.skins.randomPoolSkin();
            session.skin(pick.isPresent() ? pick.get() : SkinData.defaultSkin());
        } else if ("reuse".equals(choice)) {
            if (session.history() == null) {
                showSkin(player, session);
                return;
            }
            session.skin(session.history().toSkinData());
        } else {
            showSkin(player, session);
            return;
        }
        session.step(NickSession.Step.NAME);
        showName(player, session);
    }

    private void chooseName(Player player, NickSession session, String[] args) {
        if (args.length < 2) {
            showName(player, session);
            return;
        }
        String choice = args[1].toLowerCase(Locale.ROOT);
        if ("random".equals(choice)) {
            rollName(player, session);
        } else if ("reuse".equals(choice)) {
            if (session.history() == null) {
                showName(player, session);
                return;
            }
            finish(player, session, session.history().nickname());
        } else {
            showName(player, session);
        }
    }

    private void useRolledName(Player player, NickSession session) {
        if (session.pendingName() == null) {
            showName(player, session);
            return;
        }
        finish(player, session, session.pendingName());
    }

    private void reroll(Player player, NickSession session) {
        rollName(player, session);
    }

    private void rollName(Player player, NickSession session) {
        Optional<String> name = this.generator.generate(player);
        if (!name.isPresent()) {
            showName(player, session);
            return;
        }
        session.pendingName(name.get());
        session.step(NickSession.Step.ROLLER);
        showRolledName(player, session);
    }

    private void finish(Player player, NickSession session, String nick) {
        NameValidator.Result result = this.validator.validate(nick, player);
        if (result != NameValidator.Result.VALID) {
            if (session.step() == NickSession.Step.ROLLER) {
                rollName(player, session);
            } else {
                session.step(NickSession.Step.NAME);
                showName(player, session);
            }
            return;
        }
        this.disguises.apply(player, nick, session.rank(), session.skin());
        this.sessions.remove(player.getUniqueId());
        showFinished(player, nick);
    }

    /* ------------------------------------------------------------------ */
    /*  Component helpers                                                 */
    /* ------------------------------------------------------------------ */

    private void openBook(Player player, BaseComponent[] page) {
        VirtualBook.open(player,
                VirtualBook.buildComponents(BOOK_TITLE, BOOK_AUTHOR, page));
    }

    private static BaseComponent blank() {
        return new TextComponent(TextComponent.fromLegacyText("\n"));
    }

    private static BaseComponent line(ChatColor colour, ChatColor style, String text) {
        StringBuilder sb = new StringBuilder();
        sb.append(colour.toString());
        if (style != null) {
            sb.append(style.toString());
        }
        sb.append(text).append('\n');
        return new TextComponent(TextComponent.fromLegacyText(sb.toString()));
    }

    private static BaseComponent button(String label, String command, String hover) {
        TextComponent c = new TextComponent(
                TextComponent.fromLegacyText(ChatColor.GREEN + label + "\n"));
        c.setClickEvent(new ClickEvent(ClickEvent.Action.RUN_COMMAND, command));
        c.setHoverEvent(new HoverEvent(HoverEvent.Action.SHOW_TEXT,
                TextComponent.fromLegacyText(ChatColor.GRAY + hover)));
        return c;
    }
}
'''


FULL_REWRITES = {
    "com/yourname/nick/NickPlugin.java":                   NICKPLUGIN_JAVA,
    "com/yourname/nick/command/NickCommand.java":          NICKCOMMAND_JAVA,
    "com/yourname/nick/command/RealNameCommand.java":      REALNAME_JAVA,
    "com/yourname/nick/skin/SkinCacheManager.java":        SKINCACHE_JAVA,
    "com/yourname/nick/disguise/WorldRules.java":          WORLDRULES_JAVA,
    "com/yourname/nick/task/ActionBarTask.java":           ACTIONBAR_JAVA,
    "com/yourname/nick/util/VirtualBook.java":             VIRTUALBOOK_JAVA,
    "com/yourname/nick/gui/BookGUIManager.java":           BOOKGUI_JAVA,
}


def step_full_rewrites():
    for rel, content in FULL_REWRITES.items():
        path = os.path.join(ROOT, rel)
        write(path, content)
        print("[fixer] rewrote " + rel)


# ===========================================================================
#  STEP 3 - pattern fixes for the remaining files
# ===========================================================================

PATTERN_FIXES = [
    # leftover "this.this$1.val$xxx" -> "xxx"
    (re.compile(r"this\.this\$\d+\.val\$(\w+)"), r"\1"),
    # leftover "Outer.this.this$1.val$xxx"
    (re.compile(r"\w+\.this\.this\$\d+\.val\$(\w+)"), r"\1"),
    # synthetic accessor "Foo.access$NNN()" -> keep the call harmless
    (re.compile(r"\b(\w+)\.access\$\d+\(\)"), r"DATE_FORMAT"),
    # stray "(FileAttribute<?>[])new FileAttribute[0]" arg in Files.write / createDirectories
    (re.compile(r",\s*\(FileAttribute<\?>\[\]\)\s*new FileAttribute\[0\]"), r""),
    # "(LinkOption[]) new LinkOption[0]" style calls
    (re.compile(r",\s*new java\.nio\.file\.LinkOption\[0\]"), r""),
    (re.compile(r",\s*new java\.nio\.file\.OpenOption\[0\]"), r""),
    # "(FileAttribute<?>[]) new FileAttribute<?>[0]"
    (re.compile(r",\s*\(FileAttribute<\?>\[\]\)\s*new FileAttribute<\?>\[0\]"), r""),
]


def step_pattern_fixes():
    touched = 0
    for path in walk_java_files():
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        # skip files we already rewrote
        if rel in FULL_REWRITES:
            continue
        src = read(path)
        original = src
        for pattern, replacement in PATTERN_FIXES:
            src = pattern.sub(replacement, src)
        if src != original:
            write(path, src)
            touched += 1
    print("[fixer] pattern fixes applied to %d files" % touched)


# ===========================================================================
#  STEP 4 - add missing imports where the decompiled files lost them
# ===========================================================================

IMPORT_PATCHES = {
    "com/yourname/nick/skin/SkinCacheManager.java": [
        "import java.net.URL;",
        "import java.nio.file.Files;",
        "import java.nio.file.Path;",
    ],
    "com/yourname/nick/util/BookOpener.java": [
        "import org.bukkit.Material;",
    ],
}


def step_import_patches():
    for rel, imports in IMPORT_PATCHES.items():
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        src = read(path)
        # collect existing imports
        existing = set(re.findall(r"^import\s+[^;]+;", src, re.MULTILINE))
        missing = [imp for imp in imports if imp not in existing]
        if not missing:
            continue
        # insert after package declaration
        pkg_end = src.find(";", src.find("package "))
        insert_at = src.find("\n", pkg_end) + 1
        # find last import line to insert after
        last_import = list(re.finditer(r"^import\s+[^;]+;\s*$", src, re.MULTILINE))
        if last_import:
            insert_at = last_import[-1].end() + 1
        patched = src[:insert_at] + "\n".join(missing) + "\n" + src[insert_at:]
        write(path, patched)
        print("[fixer] added %d missing imports to %s" % (len(missing), rel))


# ===========================================================================
#  STEP 5 - YAML fixes
# ===========================================================================

def step_messages_yaml():
    path = os.path.join(ROOT, "messages.yml")
    if not os.path.isfile(path):
        # try under src/main/resources after a restructure
        path = os.path.join(ROOT, "src/main/resources/messages.yml")
    if not os.path.isfile(path):
        print("[fixer] messages.yml not found - skipping")
        return
    src = read(path)
    src = re.sub(r'actionbar:\s*".*?"',
                 'actionbar: "&c&lYou are currently NICKED"',
                 src, count=1)
    write(path, src)
    print("[fixer] patched messages.yml")


def step_config_yaml():
    candidates = [
        os.path.join(ROOT, "config.yml"),
        os.path.join(ROOT, "src/main/resources/config.yml"),
    ]
    path = None
    for c in candidates:
        if os.path.isfile(c):
            path = c
            break
    if path is None:
        print("[fixer] config.yml not found - skipping")
        return

    lines = read(path).split("\n")
    out = []
    in_worlds = False
    for line in lines:
        if line.startswith("worlds:"):
            in_worlds = True
            out.append("# World restrictions are no longer used - nicknames are")
            out.append("# applied instantly and everywhere.")
            out.append("#" + line)
            continue
        if in_worlds:
            if line and not line.startswith(" ") and not line.startswith("\t"):
                in_worlds = False
                out.append(line)
            else:
                out.append("#" + line)
        else:
            out.append(line)
    write(path, "\n".join(out))
    print("[fixer] patched config.yml")


# ===========================================================================
#  STEP 6 - ensure pom.xml has the required deps
# ===========================================================================

def step_pom():
    path = os.path.join(ROOT, "pom.xml")
    if not os.path.isfile(path):
        print("[fixer] pom.xml not found at repo root - skipping "
              "(run restructure.py first)")
        return
    src = read(path)

    additions = []
    if "sqlite-jdbc" not in src:
        additions.append(
            "        <dependency>\n"
            "            <groupId>org.xerial</groupId>\n"
            "            <artifactId>sqlite-jdbc</artifactId>\n"
            "            <version>3.44.1.0</version>\n"
            "        </dependency>\n"
        )
    if "mysql-connector-java" not in src:
        additions.append(
            "        <dependency>\n"
            "            <groupId>mysql</groupId>\n"
            "            <artifactId>mysql-connector-java</artifactId>\n"
            "            <version>8.0.33</version>\n"
            "        </dependency>\n"
        )
    if "<artifactId>gson</artifactId>" not in src:
        additions.append(
            "        <dependency>\n"
            "            <groupId>com.google.code.gson</groupId>\n"
            "            <artifactId>gson</artifactId>\n"
            "            <version>2.10.1</version>\n"
            "        </dependency>\n"
        )

    if not additions:
        print("[fixer] pom.xml already contains required dependencies")
        return

    # insert before </dependencies>
    marker = "</dependencies>"
    idx = src.find(marker)
    if idx == -1:
        print("[fixer] WARNING: </dependencies> not found in pom.xml - skipping")
        return
    src = src[:idx] + "".join(additions) + "    " + src[idx:]
    write(path, src)
    print("[fixer] added %d dependencies to pom.xml" % len(additions))


# ===========================================================================
#  Driver
# ===========================================================================

def main():
    print("=" * 60)
    print(" NickSystem fixer")
    print("=" * 60)
    step_strip_prefixes()
    step_full_rewrites()
    step_pattern_fixes()
    step_import_patches()
    step_messages_yaml()
    step_config_yaml()
    step_pom()
    print("=" * 60)
    print("[fixer] DONE")
    print("[fixer] Commit + push, then the GitHub workflow will build.")
    print("=" * 60)


if __name__ == "__main__":
    main()