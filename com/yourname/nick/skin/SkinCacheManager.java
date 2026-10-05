/*     */ package com.yourname.nick.skin;
/*     */ import com.google.gson.JsonArray;
/*     */ import com.google.gson.JsonElement;
/*     */ import com.google.gson.JsonObject;
/*     */ import com.google.gson.JsonParser;
/*     */ import com.yourname.nick.NickPlugin;
/*     */ import com.yourname.nick.model.SkinData;
/*     */ import com.yourname.nick.name.NameValidator;
/*     */ import com.yourname.nick.util.Async;
/*     */ import java.io.BufferedReader;
/*     */ import java.io.IOException;
/*     */ import java.io.InputStreamReader;
/*     */ import java.net.HttpURLConnection;
/*     */ import java.nio.charset.StandardCharsets;
/*     */ import java.nio.file.Files;
/*     */ import java.nio.file.Path;
/*     */ import java.util.ArrayList;
/*     */ import java.util.List;
/*     */ import java.util.Locale;
/*     */ import java.util.Map;
/*     */ import java.util.Optional;
/*     */ import java.util.concurrent.CompletableFuture;
/*     */ import java.util.concurrent.ConcurrentHashMap;
/*     */ import java.util.concurrent.ConcurrentMap;
/*     */ import java.util.concurrent.CopyOnWriteArrayList;
/*     */ import java.util.function.BiConsumer;
/*     */ import org.bukkit.configuration.file.FileConfiguration;
/*     */ import org.bukkit.plugin.Plugin;
/*     */ 
/*     */ public final class SkinCacheManager {
/*     */   private static final String PROFILE_URL = "https://api.mojang.com/users/profiles/minecraft/";
/*     */   private static final String SESSION_URL = "https://sessionserver.mojang.com/session/minecraft/profile/";
/*     */   private final NickPlugin plugin;
/*     */   private final long ttlMillis;
/*     */   private final int timeoutMillis;
/*     */   private final Path cacheDirectory;
/*     */   
/*     */   private static final class CachedSkin {
/*     */     final String name;
/*     */     final String value;
/*     */     
/*     */     CachedSkin(String name, String value, String signature, long fetchedAt) {
/*  43 */       this.name = name; this.value = value; this.signature = signature; this.fetchedAt = fetchedAt;
/*     */     } final String signature; final long fetchedAt;
/*     */     SkinData toSkinData(String labelPrefix) {
/*  46 */       return SkinData.custom(this.value, this.signature, labelPrefix + this.name);
/*     */     }
/*     */   }
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */   
/*  54 */   private final ConcurrentMap<String, CachedSkin> memory = new ConcurrentHashMap<>();
/*  55 */   private final ConcurrentMap<String, CompletableFuture<Optional<SkinData>>> inflight = new ConcurrentHashMap<>();
/*     */   
/*  57 */   private final List<SkinData> pool = new CopyOnWriteArrayList<>();
/*     */   
/*     */   public SkinCacheManager(NickPlugin plugin) {
/*  60 */     this.plugin = plugin;
/*  61 */     FileConfiguration fileConfiguration = plugin.getConfig();
/*  62 */     this.ttlMillis = Math.max(1L, fileConfiguration.getLong("skins.cache-ttl-minutes", 1440L)) * 60000L;
/*  63 */     this.timeoutMillis = (int)Math.max(2000L, fileConfiguration.getLong("skins.request-timeout-seconds", 10L) * 1000L);
/*  64 */     this.cacheDirectory = plugin.getDataFolder().toPath().resolve("skincache");
/*     */   }
/*     */   
/*     */   public void initialize() {
/*  68 */     FileConfiguration fileConfiguration = this.plugin.getConfig();
/*     */     
/*  70 */     for (Map<?, ?> entry : (Iterable<Map<?, ?>>)fileConfiguration.getMapList("skins.pool")) {
/*  71 */       Object value = entry.get("value");
/*  72 */       Object signature = entry.get("signature");
/*  73 */       Object label = entry.get("label");
/*  74 */       if (value == null || signature == null) {
/*  75 */         this.plugin.getLogger().warning("Ignoring skins.pool entry without value and signature.");
/*     */         continue;
/*     */       } 
/*  78 */       String name = (label == null) ? ("custom" + (this.pool.size() + 1)) : String.valueOf(label);
/*  79 */       this.pool.add(SkinData.custom(String.valueOf(value), String.valueOf(signature), "POOL:" + name));
/*     */     } 
/*     */     
/*  82 */     final List<String> names = fileConfiguration.getStringList("skins.pool-players");
/*  83 */     if (!names.isEmpty()) {
/*  84 */       Async.supply((Plugin)this.plugin, new Async.ThrowingSupplier<Integer>() {
/*     */             public Integer get() {
/*  86 */               int loaded = 0;
/*  87 */               for (String name : names) {
/*  88 */                 if (!NameValidator.isValidFormat(name)) {
/*  89 */                   SkinCacheManager.this.plugin.getLogger().warning("Ignoring invalid skins.pool-players entry '" + name + "'.");
/*     */                   continue;
/*     */                 } 
/*     */                 try {
/*  93 */                   Optional<SkinCacheManager.CachedSkin> skin = SkinCacheManager.this.resolve(name);
/*  94 */                   if (skin.isPresent()) { SkinCacheManager.this.pool.add(((SkinCacheManager.CachedSkin)skin.get()).toSkinData("POOL:")); loaded++; continue; }
/*  95 */                    SkinCacheManager.this.plugin.getLogger().warning("No skin found for pool player '" + name + "'.");
/*  96 */                 } catch (IOException e) {
/*  97 */                   SkinCacheManager.this.plugin.getLogger().warning("Could not load pool skin '" + name + "': " + e.getMessage());
/*     */                 } 
/*     */               } 
/* 100 */               return Integer.valueOf(loaded);
/*     */             }
/*     */           });
/*     */     }
/* 104 */     if (this.pool.isEmpty() && names.isEmpty()) {
/* 105 */       this.plugin.getLogger().warning("The random skin pool is empty; players choosing 'Random skin' will get the Steve/Alex skin.");
/*     */     }
/*     */   }
/*     */   
/*     */   public CompletableFuture<Optional<SkinData>> fetchByName(final String name) {
/* 110 */     if (!NameValidator.isValidFormat(name)) {
/* 111 */       return CompletableFuture.completedFuture(Optional.empty());
/*     */     }
/* 113 */     final String key = name.toLowerCase(Locale.ROOT);
/* 114 */     CompletableFuture<Optional<SkinData>> existing = this.inflight.get(key);
/* 115 */     if (existing != null) return existing;
/*     */     
/* 117 */     CompletableFuture<Optional<SkinData>> created = Async.supply((Plugin)this.plugin, new Async.ThrowingSupplier<Optional<SkinData>>() {
/*     */           public Optional<SkinData> get() throws Exception {
/* 119 */             Optional<SkinCacheManager.CachedSkin> skin = SkinCacheManager.this.resolve(name);
/* 120 */             if (skin.isPresent()) return Optional.of(((SkinCacheManager.CachedSkin)skin.get()).toSkinData("PLAYER:")); 
/* 121 */             return Optional.empty();
/*     */           }
/*     */         });
/* 124 */     this.inflight.put(key, created);
/* 125 */     created.whenComplete(new BiConsumer<Optional<SkinData>, Throwable>() {
/*     */           public void accept(Optional<SkinData> data, Throwable error) {
/* 127 */             SkinCacheManager.this.inflight.remove(key);
/*     */           }
/*     */         });
/* 130 */     return created;
/*     */   }
/*     */   
/*     */   public Optional<SkinData> randomPoolSkin() {
/* 134 */     List<SkinData> snapshot = new ArrayList<>(this.pool);
/* 135 */     if (snapshot.isEmpty()) return Optional.empty(); 
/* 136 */     return Optional.of(snapshot.get(ThreadLocalRandom.current().nextInt(snapshot.size())));
/*     */   }
/*     */   public int poolSize() {
/* 139 */     return this.pool.size();
/*     */   }
/*     */   public void shutdown() {
/* 142 */     this.memory.clear();
/* 143 */     this.inflight.clear();
/* 144 */     this.pool.clear();
/*     */   }
/*     */   
/*     */   private Optional<CachedSkin> resolve(String name) throws IOException {
/* 148 */     String key = name.toLowerCase(Locale.ROOT);
/* 149 */     CachedSkin cached = this.memory.get(key);
/* 150 */     if (cached == null) {
/* 151 */       cached = readDisk(key);
/* 152 */       if (cached != null) this.memory.put(key, cached); 
/*     */     } 
/* 154 */     if (cached != null && System.currentTimeMillis() - cached.fetchedAt < this.ttlMillis) {
/* 155 */       return Optional.of(cached);
/*     */     }
/* 157 */     Optional<CachedSkin> fresh = download(name);
/* 158 */     if (fresh.isPresent()) {
/* 159 */       this.memory.put(key, fresh.get());
/* 160 */       writeDisk(key, fresh.get());
/*     */     } 
/* 162 */     return fresh;
/*     */   }
/*     */   
/*     */   private Optional<CachedSkin> download(String name) throws IOException {
/* 166 */     String lookupBody = get("https://api.mojang.com/users/profiles/minecraft/" + name);
/* 167 */     if (lookupBody == null) return Optional.empty(); 
/*     */     try {
/* 169 */       JsonObject identity = (new JsonParser()).parse(lookupBody).getAsJsonObject();
/* 170 */       String id = identity.get("id").getAsString();
/* 171 */       String canonicalName = identity.get("name").getAsString();
/*     */       
/* 173 */       String sessionBody = get("https://sessionserver.mojang.com/session/minecraft/profile/" + id + "?unsigned=false");
/* 174 */       if (sessionBody == null) throw new IOException("Mojang session lookup failed"); 
/* 175 */       JsonArray properties = (new JsonParser()).parse(sessionBody).getAsJsonObject().getAsJsonArray("properties");
/* 176 */       for (JsonElement element : properties) {
/* 177 */         JsonObject property = element.getAsJsonObject();
/* 178 */         if ("textures".equals(property.get("name").getAsString())) {
/* 179 */           String value = property.get("value").getAsString();
/* 180 */           String signature = property.has("signature") ? property.get("signature").getAsString() : "";
/* 181 */           return Optional.of(new CachedSkin(canonicalName, value, signature, System.currentTimeMillis()));
/*     */         } 
/*     */       } 
/* 184 */       return Optional.empty();
/* 185 */     } catch (RuntimeException e) {
/* 186 */       throw new IOException("Unexpected Mojang response", e);
/*     */     } 
/*     */   }
/*     */ 
/*     */   
/*     */   private String get(String url) throws IOException {
/* 192 */     HttpURLConnection connection = (HttpURLConnection)(new URL(url)).openConnection();
/* 193 */     connection.setRequestMethod("GET");
/* 194 */     connection.setConnectTimeout(this.timeoutMillis);
/* 195 */     connection.setReadTimeout(this.timeoutMillis);
/* 196 */     connection.setRequestProperty("Accept", "application/json");
/* 197 */     connection.setRequestProperty("User-Agent", "NickSystem");
/*     */     try {
/* 199 */       int status = connection.getResponseCode();
/* 200 */       if (status == 404 || status == 204) return null; 
/* 201 */       if (status != 200) throw new IOException("HTTP " + status + " from " + url); 
/* 202 */       StringBuilder sb = new StringBuilder();
/* 203 */       BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8));
/*     */       try {
/*     */         String line;
/* 206 */         for (; (line = reader.readLine()) != null; sb.append(line));
/*     */       } finally {
/* 208 */         reader.close();
/*     */       } 
/* 210 */       return sb.toString();
/*     */     } finally {
/* 212 */       connection.disconnect();
/*     */     } 
/*     */   }
/*     */   
/*     */   private CachedSkin readDisk(String key) {
/* 217 */     Path file = this.cacheDirectory.resolve(key + ".json");
/* 218 */     if (!Files.isRegularFile(file, new java.nio.file.LinkOption[0])) return null; 
/*     */     try {
/* 220 */       String content = new String(Files.readAllBytes(file), StandardCharsets.UTF_8);
/* 221 */       JsonObject object = (new JsonParser()).parse(content).getAsJsonObject();
/* 222 */       return new CachedSkin(object
/* 223 */           .get("name").getAsString(), object
/* 224 */           .get("value").getAsString(), object
/* 225 */           .get("signature").getAsString(), object
/* 226 */           .get("fetchedAt").getAsLong());
/* 227 */     } catch (IOException|RuntimeException e) {
/* 228 */       this.plugin.getLogger().warning("Ignoring unreadable skin cache " + file.getFileName() + ": " + e.getMessage());
/* 229 */       return null;
/*     */     } 
/*     */   }
/*     */   
/*     */   private void writeDisk(String key, CachedSkin skin) {
/* 234 */     JsonObject object = new JsonObject();
/* 235 */     object.addProperty("name", skin.name);
/* 236 */     object.addProperty("value", skin.value);
/* 237 */     object.addProperty("signature", skin.signature);
/* 238 */     object.addProperty("fetchedAt", Long.valueOf(skin.fetchedAt));
/*     */     try {
/* 240 */       Files.createDirectories(this.cacheDirectory, (FileAttribute<?>[])new FileAttribute[0]);
/* 241 */       Files.write(this.cacheDirectory.resolve(key + ".json"), object.toString().getBytes(StandardCharsets.UTF_8), new java.nio.file.OpenOption[0]);
/* 242 */     } catch (IOException e) {
/* 243 */       this.plugin.getLogger().warning("Could not write skin cache for " + key + ": " + e.getMessage());
/*     */     } 
/*     */   }
/*     */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\skin\SkinCacheManager.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */