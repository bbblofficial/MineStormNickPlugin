package com.yourname.nick.storage;

import com.yourname.nick.MineStormNickPlugin;
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

/**
 * SQLite/MySQL storage on a dedicated thread.
 * Never calls Connection#isValid(int): the driver bundled with Spigot
 * 1.8.8 does not implement it and Java 17 throws AbstractMethodError.
 */
public final class StorageManager {

    private static final String COLUMNS =
            "real_uuid, real_name, nickname, rank_used, skin_source, skin_value, "
            + "skin_signature, action, created_at, ip";

    private final MineStormNickPlugin plugin;
    private final ExecutorService executor;
    private final boolean mysql;
    private final String jdbcUrl;
    private final String username;
    private final String password;
    private Connection connection;

    public StorageManager(MineStormNickPlugin plugin) {
        this.plugin = plugin;
        String type = setting("NICK_DB_TYPE",
                plugin.getConfig().getString("storage.type", "sqlite"))
                .toLowerCase(Locale.ROOT);
        this.mysql = "mysql".equals(type);
        if (this.mysql) {
            String host = setting("NICK_DB_HOST",
                    plugin.getConfig().getString("storage.mysql.host", "localhost"));
            int port = parsePort(setting("NICK_DB_PORT", String.valueOf(
                    plugin.getConfig().getInt("storage.mysql.port", 3306))));
            String database = setting("NICK_DB_NAME",
                    plugin.getConfig().getString("storage.mysql.database", "nicksystem"));
            boolean ssl = Boolean.parseBoolean(setting("NICK_DB_SSL", String.valueOf(
                    plugin.getConfig().getBoolean("storage.mysql.use-ssl", false))));
            this.username = setting("NICK_DB_USER",
                    plugin.getConfig().getString("storage.mysql.username", ""));
            this.password = setting("NICK_DB_PASSWORD",
                    plugin.getConfig().getString("storage.mysql.password", ""));
            this.jdbcUrl = "jdbc:mysql://" + host + ":" + port + "/" + database
                    + "?useSSL=" + ssl + "&allowPublicKeyRetrieval=true"
                    + "&characterEncoding=utf8&serverTimezone=UTC";
        } else {
            File file = new File(plugin.getDataFolder(),
                    plugin.getConfig().getString("storage.sqlite-file", "nick.db"));
            File parent = file.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                plugin.getLogger().warning(
                        "Could not create data folder for " + file.getName());
            }
            this.username = "";
            this.password = "";
            this.jdbcUrl = "jdbc:sqlite:" + file.getAbsolutePath();
        }
        this.executor = Executors.newSingleThreadExecutor(runnable -> {
            Thread thread = new Thread(runnable, "MineStormNickSystem-DB");
            thread.setDaemon(true);
            return thread;
        });
    }

    public CompletableFuture<Void> initialize() {
        return submit(new SqlTask<Void>() {
            @Override public Void run(Connection conn) throws SQLException {
                try (Statement s = conn.createStatement()) {
                    for (String sql : schema()) s.execute(sql);
                }
                return null;
            }
        });
    }
    public CompletableFuture<Void> insert(final NickRecord record) {
        return submit(new SqlTask<Void>() {
            @Override public Void run(Connection conn) throws SQLException {
                String sql = "INSERT INTO nick_history (" + COLUMNS + ") "
                        + "VALUES (?,?,?,?,?,?,?,?,?,?)";
                try (PreparedStatement ps = conn.prepareStatement(sql)) {
                    ps.setString(1,  record.realUuid().toString());
                    ps.setString(2,  record.realName());
                    ps.setString(3,  record.nickname());
                    ps.setString(4,  record.rankUsed());
                    ps.setString(5,  record.skinSource());
                    ps.setString(6,  record.skinValue());
                    ps.setString(7,  record.skinSignature());
                    ps.setString(8,  record.action());
                    ps.setLong(9,    record.createdAt());
                    ps.setString(10, record.ip());
                    ps.executeUpdate();
                }
                return null;
            }
        });
    }
    public CompletableFuture<Optional<NickRecord>> findLatestForPlayer(UUID uuid) {
        return queryOne("SELECT " + COLUMNS + " FROM nick_history "
                + "WHERE real_uuid = ? ORDER BY id DESC LIMIT 1", uuid.toString());
    }
    public CompletableFuture<Optional<NickRecord>> findLastSetForPlayer(UUID uuid) {
        return queryOne("SELECT " + COLUMNS + " FROM nick_history "
                + "WHERE real_uuid = ? AND action = 'SET' ORDER BY id DESC LIMIT 1",
                uuid.toString());
    }
    public CompletableFuture<Optional<NickRecord>> findLatestByNickname(String nickname) {
        return queryOne("SELECT " + COLUMNS + " FROM nick_history "
                + "WHERE LOWER(nickname) = LOWER(?) AND action = 'SET' "
                + "ORDER BY id DESC LIMIT 1", nickname);
    }
    public void close() {
        try {
            this.executor.execute(new Runnable() {
                @Override public void run() { closeConnection(); }
            });
        } catch (RejectedExecutionException ignored) { return; }
        this.executor.shutdown();
        try {
            if (!this.executor.awaitTermination(5L, TimeUnit.SECONDS)) {
                this.plugin.getLogger().warning(
                        "Database executor did not terminate in time; some writes may be lost.");
                this.executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            this.executor.shutdownNow();
        }
    }

    @FunctionalInterface
    public interface SqlTask<T> { T run(Connection connection) throws SQLException; }

    private <T> CompletableFuture<T> submit(final SqlTask<T> task) {
        final CompletableFuture<T> future = new CompletableFuture<T>();
        try {
            this.executor.execute(new Runnable() {
                @Override public void run() {
                    try { future.complete(runWithRetry(task)); }
                    catch (Throwable t) { future.completeExceptionally(t); }
                }
            });
        } catch (RejectedExecutionException e) { future.completeExceptionally(e); }
        return future;
    }
    private <T> T runWithRetry(SqlTask<T> task) throws SQLException {
        try { return task.run(openConnection()); }
        catch (Throwable first) {
            closeConnection();
            this.plugin.getLogger().log(Level.FINE,
                    "DB operation failed, retrying once: " + first);
            return task.run(openConnection());
        }
    }
    private CompletableFuture<Optional<NickRecord>> queryOne(
            final String sql, final String parameter) {
        return submit(new SqlTask<Optional<NickRecord>>() {
            @Override public Optional<NickRecord> run(Connection conn) throws SQLException {
                try (PreparedStatement ps = conn.prepareStatement(sql)) {
                    ps.setString(1, parameter);
                    try (ResultSet rs = ps.executeQuery()) {
                        return rs.next() ? Optional.of(map(rs))
                                         : Optional.<NickRecord>empty();
                    }
                }
            }
        });
    }
    private Connection openConnection() throws SQLException {
        if (this.connection != null && !this.connection.isClosed()
                && probe(this.connection)) {
            return this.connection;
        }
        closeConnection();
        try {
            Class.forName(this.mysql ? "com.mysql.cj.jdbc.Driver" : "org.sqlite.JDBC");
        } catch (ClassNotFoundException e) {
            throw new SQLException("JDBC driver not available on this server", e);
        }
        this.connection = this.mysql
                ? DriverManager.getConnection(this.jdbcUrl, this.username, this.password)
                : DriverManager.getConnection(this.jdbcUrl);
        if (!this.mysql) {
            try (Statement s = this.connection.createStatement()) {
                s.execute("PRAGMA journal_mode=WAL");
                s.execute("PRAGMA busy_timeout=5000");
            }
        }
        return this.connection;
    }
    private static boolean probe(Connection connection) {
        try (Statement s = connection.createStatement()) {
            s.execute("SELECT 1");
            return true;
        } catch (SQLException | AbstractMethodError e) { return false; }
    }
    private void closeConnection() {
        if (this.connection == null) return;
        try { this.connection.close(); }
        catch (SQLException e) {
            this.plugin.getLogger().log(Level.WARNING,
                    "Failed to close database connection", e);
        } finally { this.connection = null; }
    }
    private List<String> schema() {
        List<String> out = new ArrayList<String>();
        if (this.mysql) {
            out.add("CREATE TABLE IF NOT EXISTS nick_history ("
                    + "id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,"
                    + "real_uuid VARCHAR(36) NOT NULL,"
                    + "real_name VARCHAR(16) NOT NULL,"
                    + "nickname VARCHAR(16) NOT NULL,"
                    + "rank_used VARCHAR(16) NOT NULL,"
                    + "skin_source VARCHAR(64) NOT NULL,"
                    + "skin_value MEDIUMTEXT,"
                    + "skin_signature MEDIUMTEXT,"
                    + "action VARCHAR(8) NOT NULL,"
                    + "created_at BIGINT NOT NULL,"
                    + "ip VARCHAR(45) NOT NULL,"
                    + "INDEX idx_nick_history_uuid (real_uuid),"
                    + "INDEX idx_nick_history_nick (nickname)"
                    + ") DEFAULT CHARSET=utf8mb4");
        } else {
            out.add("CREATE TABLE IF NOT EXISTS nick_history ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    + "real_uuid TEXT NOT NULL,"
                    + "real_name TEXT NOT NULL,"
                    + "nickname TEXT NOT NULL,"
                    + "rank_used TEXT NOT NULL,"
                    + "skin_source TEXT NOT NULL,"
                    + "skin_value TEXT,"
                    + "skin_signature TEXT,"
                    + "action TEXT NOT NULL,"
                    + "created_at INTEGER NOT NULL,"
                    + "ip TEXT NOT NULL)");
            out.add("CREATE INDEX IF NOT EXISTS idx_nick_history_uuid "
                    + "ON nick_history (real_uuid)");
            out.add("CREATE INDEX IF NOT EXISTS idx_nick_history_nick "
                    + "ON nick_history (nickname)");
        }
        return out;
    }
    private static NickRecord map(ResultSet rs) throws SQLException {
        return new NickRecord(
                UUID.fromString(rs.getString("real_uuid")),
                rs.getString("real_name"),
                rs.getString("nickname"),
                rs.getString("rank_used"),
                rs.getString("skin_source"),
                emptyIfNull(rs.getString("skin_value")),
                emptyIfNull(rs.getString("skin_signature")),
                rs.getString("action"),
                rs.getLong("created_at"),
                rs.getString("ip"));
    }
    private static String emptyIfNull(String value) { return value == null ? "" : value; }
    private static String setting(String key, String fallback) {
        String fromEnv = System.getenv(key);
        if (fromEnv != null && !fromEnv.trim().isEmpty()) return fromEnv.trim();
        return fallback == null ? "" : fallback;
    }
    private static int parsePort(String value) {
        try { return Integer.parseInt(value.trim()); }
        catch (NumberFormatException e) { return 3306; }
    }
}
