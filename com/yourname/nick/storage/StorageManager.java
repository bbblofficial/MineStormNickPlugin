/*     */ package com.yourname.nick.storage;
/*     */ 
/*     */ import com.yourname.nick.NickPlugin;
/*     */ import com.yourname.nick.model.NickRecord;
/*     */ import java.io.File;
/*     */ import java.sql.Connection;
/*     */ import java.sql.DriverManager;
/*     */ import java.sql.PreparedStatement;
/*     */ import java.sql.ResultSet;
/*     */ import java.sql.SQLException;
/*     */ import java.sql.Statement;
/*     */ import java.util.ArrayList;
/*     */ import java.util.List;
/*     */ import java.util.Locale;
/*     */ import java.util.Optional;
/*     */ import java.util.UUID;
/*     */ import java.util.concurrent.CompletableFuture;
/*     */ import java.util.concurrent.ExecutorService;
/*     */ import java.util.concurrent.Executors;
/*     */ import java.util.concurrent.RejectedExecutionException;
/*     */ import java.util.concurrent.TimeUnit;
/*     */ import java.util.logging.Level;
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ public final class StorageManager
/*     */ {
/*     */   private static final String COLUMNS = "real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip";
/*     */   private final NickPlugin plugin;
/*     */   private final ExecutorService executor;
/*     */   private final boolean mysql;
/*     */   private final String jdbcUrl;
/*     */   private final String username;
/*     */   private final String password;
/*     */   private Connection connection;
/*     */   
/*     */   public StorageManager(NickPlugin plugin) {
/*  49 */     this.plugin = plugin;
/*  50 */     String type = setting("NICK_DB_TYPE", plugin.getConfig().getString("storage.type", "sqlite")).toLowerCase(Locale.ROOT);
/*  51 */     this.mysql = "mysql".equals(type);
/*  52 */     if (this.mysql) {
/*  53 */       String host = setting("NICK_DB_HOST", plugin.getConfig().getString("storage.mysql.host", "localhost"));
/*  54 */       int port = parsePort(setting("NICK_DB_PORT", String.valueOf(plugin.getConfig().getInt("storage.mysql.port", 3306))));
/*  55 */       String database = setting("NICK_DB_NAME", plugin.getConfig().getString("storage.mysql.database", "nicksystem"));
/*  56 */       boolean ssl = Boolean.parseBoolean(setting("NICK_DB_SSL", 
/*  57 */             String.valueOf(plugin.getConfig().getBoolean("storage.mysql.use-ssl", false))));
/*  58 */       this.username = setting("NICK_DB_USER", plugin.getConfig().getString("storage.mysql.username", ""));
/*  59 */       this.password = setting("NICK_DB_PASSWORD", plugin.getConfig().getString("storage.mysql.password", ""));
/*  60 */       this.jdbcUrl = "jdbc:mysql://" + host + ":" + port + "/" + database + "?useSSL=" + ssl + "&allowPublicKeyRetrieval=true&characterEncoding=utf8&serverTimezone=UTC";
/*     */     } else {
/*     */       
/*  63 */       File file = new File(plugin.getDataFolder(), plugin.getConfig().getString("storage.sqlite-file", "nick.db"));
/*  64 */       this.username = "";
/*  65 */       this.password = "";
/*  66 */       this.jdbcUrl = "jdbc:sqlite:" + file.getAbsolutePath();
/*     */     } 
/*  68 */     this.executor = Executors.newSingleThreadExecutor(runnable -> {
/*     */           Thread thread = new Thread(runnable, "NickSystem-Database");
/*     */           thread.setDaemon(true);
/*     */           return thread;
/*     */         });
/*     */   }
/*     */   
/*     */   public CompletableFuture<Void> initialize() {
/*  76 */     return submit(new SqlTask<Void>() {
/*     */           public Void run(Connection conn) throws SQLException {
/*  78 */             Statement statement = conn.createStatement(); 
/*  79 */             try { for (String sql : StorageManager.this.schema()) statement.execute(sql); 
/*  80 */               if (statement != null) statement.close();  } catch (Throwable throwable) { if (statement != null)
/*  81 */                 try { statement.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; }  return null;
/*     */           }
/*     */         });
/*     */   }
/*     */   
/*     */   public CompletableFuture<Void> insert(final NickRecord record) {
/*  87 */     return submit(new SqlTask<Void>() {
/*     */           public Void run(Connection conn) throws SQLException {
/*  89 */             String sql = "INSERT INTO nick_history (real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip) VALUES (?,?,?,?,?,?,?,?,?,?)";
/*  90 */             PreparedStatement statement = conn.prepareStatement(sql); 
/*  91 */             try { statement.setString(1, record.realUuid().toString());
/*  92 */               statement.setString(2, record.realName());
/*  93 */               statement.setString(3, record.nickname());
/*  94 */               statement.setString(4, record.rankUsed());
/*  95 */               statement.setString(5, record.skinSource());
/*  96 */               statement.setString(6, record.skinValue());
/*  97 */               statement.setString(7, record.skinSignature());
/*  98 */               statement.setString(8, record.action());
/*  99 */               statement.setLong(9, record.createdAt());
/* 100 */               statement.setString(10, record.ip());
/* 101 */               statement.executeUpdate();
/* 102 */               if (statement != null) statement.close();  } catch (Throwable throwable) { if (statement != null)
/* 103 */                 try { statement.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; }  return null;
/*     */           }
/*     */         });
/*     */   } @FunctionalInterface
/*     */   public static interface SqlTask<T> {
/*     */     T run(Connection param1Connection) throws SQLException; } public CompletableFuture<Optional<NickRecord>> findLatestForPlayer(UUID uuid) {
/* 109 */     return queryOne("SELECT real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip FROM nick_history WHERE real_uuid = ? ORDER BY id DESC LIMIT 1", uuid
/* 110 */         .toString());
/*     */   }
/*     */   
/*     */   public CompletableFuture<Optional<NickRecord>> findLastSetForPlayer(UUID uuid) {
/* 114 */     return queryOne("SELECT real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip FROM nick_history WHERE real_uuid = ? AND action = 'SET' ORDER BY id DESC LIMIT 1", uuid
/* 115 */         .toString());
/*     */   }
/*     */   
/*     */   public CompletableFuture<Optional<NickRecord>> findLatestByNickname(String nickname) {
/* 119 */     return queryOne("SELECT real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip FROM nick_history WHERE LOWER(nickname) = LOWER(?) AND action = 'SET' ORDER BY id DESC LIMIT 1", nickname);
/*     */   }
/*     */ 
/*     */   
/*     */   public void close() {
/*     */     try {
/* 125 */       this.executor.execute(new Runnable() {
/* 126 */             public void run() { StorageManager.this.closeConnection(); }
/*     */           });
/* 128 */     } catch (RejectedExecutionException ignored) {
/*     */       return;
/*     */     } 
/* 131 */     this.executor.shutdown();
/*     */     try {
/* 133 */       if (!this.executor.awaitTermination(5L, TimeUnit.SECONDS)) {
/* 134 */         this.plugin.getLogger().warning("Database executor did not terminate in time; some writes may be lost.");
/* 135 */         this.executor.shutdownNow();
/*     */       } 
/* 137 */     } catch (InterruptedException exception) {
/* 138 */       Thread.currentThread().interrupt();
/* 139 */       this.executor.shutdownNow();
/*     */     } 
/*     */   }
/*     */   
/*     */   private CompletableFuture<Optional<NickRecord>> queryOne(final String sql, final String parameter) {
/* 144 */     return submit(new SqlTask<Optional<NickRecord>>()
/*     */         {
/* 146 */           public Optional<NickRecord> run(Connection conn) throws SQLException { PreparedStatement statement = conn.prepareStatement(sql); 
/* 147 */             try { statement.setString(1, parameter);
/* 148 */               ResultSet rs = statement.executeQuery(); 
/* 149 */               try { if (rs.next()) { Optional<NickRecord> optional1 = Optional.of(StorageManager.map(rs));
/*     */                   
/* 151 */                   if (rs != null) rs.close(); 
/* 152 */                   if (statement != null) statement.close();  return optional1; }  Optional<?> optional = Optional.empty(); if (rs != null) rs.close();  if (statement != null) statement.close();  return (Optional)optional; } catch (Throwable throwable) { if (rs != null)
/*     */                   try { rs.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; }  }
/*     */             catch (Throwable throwable) { if (statement != null)
/*     */                 try { statement.close(); }
/*     */                 catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }
/*     */                   throw throwable; }
/* 158 */              } }); } private <T> CompletableFuture<T> submit(final SqlTask<T> task) { final CompletableFuture<T> future = new CompletableFuture<>();
/*     */     try {
/* 160 */       this.executor.execute(new Runnable() {
/*     */             public void run() {
/*     */               try {
/* 163 */                 future.complete(task.run(StorageManager.this.openConnection()));
/* 164 */               } catch (Throwable throwable) {
/* 165 */                 future.completeExceptionally(throwable);
/*     */               } 
/*     */             }
/*     */           });
/* 169 */     } catch (RejectedExecutionException exception) {
/* 170 */       future.completeExceptionally(exception);
/*     */     } 
/* 172 */     return future; }
/*     */ 
/*     */   
/*     */   private Connection openConnection() throws SQLException {
/* 176 */     if (this.connection != null && !this.connection.isClosed() && this.connection.isValid(2)) {
/* 177 */       return this.connection;
/*     */     }
/* 179 */     closeConnection();
/*     */     try {
/* 181 */       Class.forName(this.mysql ? "com.mysql.cj.jdbc.Driver" : "org.sqlite.JDBC");
/* 182 */     } catch (ClassNotFoundException exception) {
/* 183 */       throw new SQLException("JDBC driver not available on this server", exception);
/*     */     } 
/* 185 */     this
/*     */       
/* 187 */       .connection = this.mysql ? DriverManager.getConnection(this.jdbcUrl, this.username, this.password) : DriverManager.getConnection(this.jdbcUrl);
/* 188 */     if (!this.mysql) {
/* 189 */       Statement statement = this.connection.createStatement(); 
/* 190 */       try { statement.execute("PRAGMA journal_mode=WAL");
/* 191 */         if (statement != null) statement.close();  } catch (Throwable throwable) { if (statement != null)
/*     */           try { statement.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; } 
/* 193 */     }  return this.connection;
/*     */   }
/*     */   
/*     */   private void closeConnection() {
/* 197 */     if (this.connection == null)
/*     */       return;  try {
/* 199 */       this.connection.close();
/* 200 */     } catch (SQLException exception) {
/* 201 */       this.plugin.getLogger().log(Level.WARNING, "Failed to close database connection", exception);
/*     */     } 
/* 203 */     this.connection = null;
/*     */   }
/*     */   
/*     */   private List<String> schema() {
/* 207 */     List<String> out = new ArrayList<>();
/* 208 */     if (this.mysql) {
/* 209 */       out.add("CREATE TABLE IF NOT EXISTS nick_history (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,real_uuid VARCHAR(36) NOT NULL,real_name VARCHAR(16) NOT NULL,nickname VARCHAR(16) NOT NULL,rank_used VARCHAR(16) NOT NULL,skin_source VARCHAR(64) NOT NULL,skin_value MEDIUMTEXT,skin_signature MEDIUMTEXT,action VARCHAR(8) NOT NULL,created_at BIGINT NOT NULL,ip VARCHAR(45) NOT NULL,INDEX idx_nick_history_uuid (real_uuid),INDEX idx_nick_history_nick (nickname)) DEFAULT CHARSET=utf8mb4");
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */     
/*     */     }
/*     */     else {
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */       
/* 225 */       out.add("CREATE TABLE IF NOT EXISTS nick_history (id INTEGER PRIMARY KEY AUTOINCREMENT,real_uuid TEXT NOT NULL,real_name TEXT NOT NULL,nickname TEXT NOT NULL,rank_used TEXT NOT NULL,skin_source TEXT NOT NULL,skin_value TEXT,skin_signature TEXT,action TEXT NOT NULL,created_at INTEGER NOT NULL,ip TEXT NOT NULL)");
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */       
/* 237 */       out.add("CREATE INDEX IF NOT EXISTS idx_nick_history_uuid ON nick_history (real_uuid)");
/* 238 */       out.add("CREATE INDEX IF NOT EXISTS idx_nick_history_nick ON nick_history (nickname)");
/*     */     } 
/* 240 */     return out;
/*     */   }
/*     */   
/*     */   private static NickRecord map(ResultSet rs) throws SQLException {
/* 244 */     return new NickRecord(
/* 245 */         UUID.fromString(rs.getString("real_uuid")), rs
/* 246 */         .getString("real_name"), rs
/* 247 */         .getString("nickname"), rs
/* 248 */         .getString("rank_used"), rs
/* 249 */         .getString("skin_source"), 
/* 250 */         emptyIfNull(rs.getString("skin_value")), 
/* 251 */         emptyIfNull(rs.getString("skin_signature")), rs
/* 252 */         .getString("action"), rs
/* 253 */         .getLong("created_at"), rs
/* 254 */         .getString("ip"));
/*     */   }
/*     */   private static String emptyIfNull(String value) {
/* 257 */     return (value == null) ? "" : value;
/*     */   }
/*     */   private static String setting(String environmentKey, String fallback) {
/* 260 */     String fromEnvironment = System.getenv(environmentKey);
/* 261 */     if (fromEnvironment != null && !fromEnvironment.trim().isEmpty()) {
/* 262 */       return fromEnvironment.trim();
/*     */     }
/* 264 */     return (fallback == null) ? "" : fallback;
/*     */   }
/*     */   
/*     */   private static int parsePort(String value) {
/*     */     try {
/* 269 */       return Integer.parseInt(value.trim());
/* 270 */     } catch (NumberFormatException exception) {
/* 271 */       return 3306;
/*     */     } 
/*     */   }
/*     */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\storage\StorageManager.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */