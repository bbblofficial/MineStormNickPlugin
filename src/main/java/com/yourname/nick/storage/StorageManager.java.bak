package com.yourname.nick.storage;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.model.NickRecord;
import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;














public final class StorageManager
{
  private static final String COLUMNS = "real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip";
  private final NickPlugin plugin;
  private final ExecutorService executor;
  private final boolean mysql;
  private final String jdbcUrl;
  private final String username;
  private final String password;
  private Connection connection;
  
  public StorageManager(NickPlugin plugin) {
    this.plugin = plugin;
    String type = setting("NICK_DB_TYPE", plugin.getConfig().getString("storage.type", "sqlite")).toLowerCase(Locale.ROOT);
    this.mysql = "mysql".equals(type);
    if (this.mysql) {
      String host = setting("NICK_DB_HOST", plugin.getConfig().getString("storage.mysql.host", "localhost"));
      int port = parsePort(setting("NICK_DB_PORT", String.valueOf(plugin.getConfig().getInt("storage.mysql.port", 3306))));
      String database = setting("NICK_DB_NAME", plugin.getConfig().getString("storage.mysql.database", "nicksystem"));
      boolean ssl = Boolean.parseBoolean(setting("NICK_DB_SSL", 
            String.valueOf(plugin.getConfig().getBoolean("storage.mysql.use-ssl", false))));
      this.username = setting("NICK_DB_USER", plugin.getConfig().getString("storage.mysql.username", ""));
      this.password = setting("NICK_DB_PASSWORD", plugin.getConfig().getString("storage.mysql.password", ""));
      this.jdbcUrl = "jdbc:mysql://" + host + ":" + port + "/" + database + "?useSSL=" + ssl + "&allowPublicKeyRetrieval=true&characterEncoding=utf8&serverTimezone=UTC";
    } else {
      
      File file = new File(plugin.getDataFolder(), plugin.getConfig().getString("storage.sqlite-file", "nick.db"));
      this.username = "";
      this.password = "";
      this.jdbcUrl = "jdbc:sqlite:" + file.getAbsolutePath();
    } 
    this.executor = Executors.newSingleThreadExecutor(runnable -> {
          Thread thread = new Thread(runnable, "NickSystem-Database");
          thread.setDaemon(true);
          return thread;
        });
  }
  
  public CompletableFuture<Void> initialize() {
    return submit(new SqlTask<Void>() {
          public Void run(Connection conn) throws SQLException {
            Statement statement = conn.createStatement(); 
            try { for (String sql : StorageManager.this.schema()) statement.execute(sql); 
              if (statement != null) statement.close();  } catch (Throwable throwable) { if (statement != null)
                try { statement.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; }  return null;
          }
        });
  }
  
  public CompletableFuture<Void> insert(final NickRecord record) {
    return submit(new SqlTask<Void>() {
          public Void run(Connection conn) throws SQLException {
            String sql = "INSERT INTO nick_history (real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip) VALUES (?,?,?,?,?,?,?,?,?,?)";
            PreparedStatement statement = conn.prepareStatement(sql); 
            try { statement.setString(1, record.realUuid().toString());
              statement.setString(2, record.realName());
              statement.setString(3, record.nickname());
              statement.setString(4, record.rankUsed());
              statement.setString(5, record.skinSource());
              statement.setString(6, record.skinValue());
              statement.setString(7, record.skinSignature());
              statement.setString(8, record.action());
              statement.setLong(9, record.createdAt());
              statement.setString(10, record.ip());
              statement.executeUpdate();
              if (statement != null) statement.close();  } catch (Throwable throwable) { if (statement != null)
                try { statement.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; }  return null;
          }
        });
  } @FunctionalInterface
  public static interface SqlTask<T> {
    T run(Connection param1Connection) throws SQLException; } public CompletableFuture<Optional<NickRecord>> findLatestForPlayer(UUID uuid) {
    return queryOne("SELECT real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip FROM nick_history WHERE real_uuid = ? ORDER BY id DESC LIMIT 1", uuid
        .toString());
  }
  
  public CompletableFuture<Optional<NickRecord>> findLastSetForPlayer(UUID uuid) {
    return queryOne("SELECT real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip FROM nick_history WHERE real_uuid = ? AND action = 'SET' ORDER BY id DESC LIMIT 1", uuid
        .toString());
  }
  
  public CompletableFuture<Optional<NickRecord>> findLatestByNickname(String nickname) {
    return queryOne("SELECT real_uuid, real_name, nickname, rank_used, skin_source, skin_value, skin_signature, action, created_at, ip FROM nick_history WHERE LOWER(nickname) = LOWER(?) AND action = 'SET' ORDER BY id DESC LIMIT 1", nickname);
  }

  
  public void close() {
    try {
      this.executor.execute(new Runnable() {
            public void run() { StorageManager.this.closeConnection(); }
          });
    } catch (RejectedExecutionException ignored) {
      return;
    } 
    this.executor.shutdown();
    try {
      if (!this.executor.awaitTermination(5L, TimeUnit.SECONDS)) {
        this.plugin.getLogger().warning("Database executor did not terminate in time; some writes may be lost.");
        this.executor.shutdownNow();
      } 
    } catch (InterruptedException exception) {
      Thread.currentThread().interrupt();
      this.executor.shutdownNow();
    } 
  }
  
  private CompletableFuture<Optional<NickRecord>> queryOne(final String sql, final String parameter) {
    return submit(new SqlTask<Optional<NickRecord>>()
        {
          public Optional<NickRecord> run(Connection conn) throws SQLException { PreparedStatement statement = conn.prepareStatement(sql); 
            try { statement.setString(1, parameter);
              ResultSet rs = statement.executeQuery(); 
              try { if (rs.next()) { Optional<NickRecord> optional1 = Optional.of(StorageManager.map(rs));
                  
                  if (rs != null) rs.close(); 
                  if (statement != null) statement.close();  return optional1; }  Optional<?> optional = Optional.empty(); if (rs != null) rs.close();  if (statement != null) statement.close();  return (Optional)optional; } catch (Throwable throwable) { if (rs != null)
                  try { rs.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; }  }
            catch (Throwable throwable) { if (statement != null)
                try { statement.close(); }
                catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }
                  throw throwable; }
             } }); } private <T> CompletableFuture<T> submit(final SqlTask<T> task) { final CompletableFuture<T> future = new CompletableFuture<>();
    try {
      this.executor.execute(new Runnable() {
            public void run() {
              try {
                future.complete(task.run(StorageManager.this.openConnection()));
              } catch (Throwable throwable) {
                future.completeExceptionally(throwable);
              } 
            }
          });
    } catch (RejectedExecutionException exception) {
      future.completeExceptionally(exception);
    } 
    return future; }

  
  private Connection openConnection() throws SQLException {
    if (this.connection != null && !this.connection.isClosed() && this.connection.isValid(2)) {
      return this.connection;
    }
    closeConnection();
    try {
      Class.forName(this.mysql ? "com.mysql.cj.jdbc.Driver" : "org.sqlite.JDBC");
    } catch (ClassNotFoundException exception) {
      throw new SQLException("JDBC driver not available on this server", exception);
    } 
    this
      
      .connection = this.mysql ? DriverManager.getConnection(this.jdbcUrl, this.username, this.password) : DriverManager.getConnection(this.jdbcUrl);
    if (!this.mysql) {
      Statement statement = this.connection.createStatement(); 
      try { statement.execute("PRAGMA journal_mode=WAL");
        if (statement != null) statement.close();  } catch (Throwable throwable) { if (statement != null)
          try { statement.close(); } catch (Throwable throwable1) { throwable.addSuppressed(throwable1); }   throw throwable; } 
    }  return this.connection;
  }
  
  private void closeConnection() {
    if (this.connection == null)
      return;  try {
      this.connection.close();
    } catch (SQLException exception) {
      this.plugin.getLogger().log(Level.WARNING, "Failed to close database connection", exception);
    } 
    this.connection = null;
  }
  
  private List<String> schema() {
    List<String> out = new ArrayList<>();
    if (this.mysql) {
      out.add("CREATE TABLE IF NOT EXISTS nick_history (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,real_uuid VARCHAR(36) NOT NULL,real_name VARCHAR(16) NOT NULL,nickname VARCHAR(16) NOT NULL,rank_used VARCHAR(16) NOT NULL,skin_source VARCHAR(64) NOT NULL,skin_value MEDIUMTEXT,skin_signature MEDIUMTEXT,action VARCHAR(8) NOT NULL,created_at BIGINT NOT NULL,ip VARCHAR(45) NOT NULL,INDEX idx_nick_history_uuid (real_uuid),INDEX idx_nick_history_nick (nickname)) DEFAULT CHARSET=utf8mb4");





    
    }
    else {






      
      out.add("CREATE TABLE IF NOT EXISTS nick_history (id INTEGER PRIMARY KEY AUTOINCREMENT,real_uuid TEXT NOT NULL,real_name TEXT NOT NULL,nickname TEXT NOT NULL,rank_used TEXT NOT NULL,skin_source TEXT NOT NULL,skin_value TEXT,skin_signature TEXT,action TEXT NOT NULL,created_at INTEGER NOT NULL,ip TEXT NOT NULL)");










      
      out.add("CREATE INDEX IF NOT EXISTS idx_nick_history_uuid ON nick_history (real_uuid)");
      out.add("CREATE INDEX IF NOT EXISTS idx_nick_history_nick ON nick_history (nickname)");
    } 
    return out;
  }
  
  private static NickRecord map(ResultSet rs) throws SQLException {
    return new NickRecord(
        UUID.fromString(rs.getString("real_uuid")), rs
        .getString("real_name"), rs
        .getString("nickname"), rs
        .getString("rank_used"), rs
        .getString("skin_source"), 
        emptyIfNull(rs.getString("skin_value")), 
        emptyIfNull(rs.getString("skin_signature")), rs
        .getString("action"), rs
        .getLong("created_at"), rs
        .getString("ip"));
  }
  private static String emptyIfNull(String value) {
    return (value == null) ? "" : value;
  }
  private static String setting(String environmentKey, String fallback) {
    String fromEnvironment = System.getenv(environmentKey);
    if (fromEnvironment != null && !fromEnvironment.trim().isEmpty()) {
      return fromEnvironment.trim();
    }
    return (fallback == null) ? "" : fallback;
  }
  
  private static int parsePort(String value) {
    try {
      return Integer.parseInt(value.trim());
    } catch (NumberFormatException exception) {
      return 3306;
    } 
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\storage\StorageManager.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */