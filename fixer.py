#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MineStormNickSystem - SQLite AbstractMethodError fixer.

Root cause
----------
Spigot 1.8.8 ships org.sqlite.JDBC:3.7.2. That driver does not implement
java.sql.Connection#isValid(int). On Java 17+ the JVM enforces the
interface contract and every call throws:

    java.lang.AbstractMethodError: Receiver class org.sqlite.Conn does not
    define or inherit an implementation of the resolved method
    'abstract boolean isValid(int)' of interface java.sql.Connection

The previous StorageManager.openConnection() called connection.isValid(2)
on every access, so every insert/query after the first failed.

What this script does
---------------------
1.  Rewrites StorageManager.java so it:
      - probes the live connection with a trivial `SELECT 1` instead of
        isValid(int);
      - retries a failed task once after closing the bad connection;
      - enables SQLite PRAGMA journal_mode=WAL and busy_timeout=5000.
2.  Patches pom.xml to add org.xerial:sqlite-jdbc:3.44.1.0 (compiled for
    Java 8, has a working isValid) and shades it under
    com.yourname.nick.libs.sqlite so the server's copy is never used.
3.  Idempotent: running it again reports SKIP for anything already fixed.

Run from the plugin project root (folder containing pom.xml).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def find_project_root() -> Path:
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "pom.xml").is_file():
            return candidate
    raise SystemExit("FATAL: pom.xml not found. Run from the plugin project root.")


ROOT = find_project_root()
SRC_JAVA = ROOT / "src" / "main" / "java"


def find_package_dir() -> Path:
    for name in ("MineStormNickPlugin.java", "NickPlugin.java"):
        preferred = SRC_JAVA / "com" / "yourname" / "nick"
        if (preferred / name).is_file():
            return preferred
    for name in ("MineStormNickPlugin.java", "NickPlugin.java"):
        for path in SRC_JAVA.rglob(name):
            return path.parent
    return SRC_JAVA / "com" / "yourname" / "nick"


PACKAGE_DIR = find_package_dir()

LOG: list[tuple[str, str]] = []


def log(level: str, message: str) -> None:
    LOG.append((level, message))
    print(f"[{level:<4}] {message}")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path, content: str, *, dry: bool, backup: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            existing = None
        if existing is not None and sha(existing) == sha(content):
            log("SKIP", f"{path.relative_to(ROOT)} (up to date)")
            return "skipped"
        if dry:
            log("DRY ", f"would update {path.relative_to(ROOT)}")
            return "updated"
        if backup:
            try:
                shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
            except OSError as exc:
                log("WARN", f"backup failed for {path}: {exc}")
        path.write_text(content, encoding="utf-8", newline="\n")
        log("OK  ", f"updated {path.relative_to(ROOT)}")
        return "updated"
    if dry:
        log("DRY ", f"would create {path.relative_to(ROOT)}")
        return "created"
    path.write_text(content, encoding="utf-8", newline="\n")
    log("OK  ", f"created {path.relative_to(ROOT)}")
    return "created"


# ═══════════════════════════════════════════════════════════════════════════
#  StorageManager.java  (full, portable replacement)
# ═══════════════════════════════════════════════════════════════════════════

JAVA_STORAGE_MANAGER = r'''package com.yourname.nick.storage;

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
 * Thread-confined SQLite/MySQL storage.
 *
 * <p><b>Java 17 fix:</b> {@link Connection#isValid(int)} is not implemented
 * by the SQLite driver bundled with Spigot 1.8.8
 * ({@code org.sqlite.JDBC:3.7.2}). Under Java 17 the JVM throws
 * {@link AbstractMethodError} the moment that method is invoked. This
 * class therefore performs the connection check with
 * {@code isClosed()} plus a trivial {@code SELECT 1} probe, which every
 * driver from Java 6 onwards supports.</p>
 *
 * <p>If a task fails for any reason, the connection is closed and the task
 * is retried once. That keeps a single transient failure from killing the
 * entire storage subsystem.</p>
 */
public final class StorageManager {

    private static final String COLUMNS =
            "real_uuid, real_name, nickname, rank_used, skin_source, skin_value, " +
            "skin_signature, action, created_at, ip";

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
                    + "?useSSL=" + ssl
                    + "&allowPublicKeyRetrieval=true"
                    + "&characterEncoding=utf8"
                    + "&serverTimezone=UTC";
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

    /* ------------------------------------------------------------------ */
    /*  Public API                                                        */
    /* ------------------------------------------------------------------ */

    public CompletableFuture<Void> initialize() {
        return submit(new SqlTask<Void>() {
            @Override public Void run(Connection conn) throws SQLException {
                try (Statement s = conn.createStatement()) {
                    for (String sql : schema()) {
                        s.execute(sql);
                    }
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
                + "WHERE real_uuid = ? ORDER BY id DESC LIMIT 1",
                uuid.toString());
    }

    public CompletableFuture<Optional<NickRecord>> findLastSetForPlayer(UUID uuid) {
        return queryOne("SELECT " + COLUMNS + " FROM nick_history "
                + "WHERE real_uuid = ? AND action = 'SET' ORDER BY id DESC LIMIT 1",
                uuid.toString());
    }

    public CompletableFuture<Optional<NickRecord>> findLatestByNickname(String nickname) {
        return queryOne("SELECT " + COLUMNS + " FROM nick_history "
                + "WHERE LOWER(nickname) = LOWER(?) AND action = 'SET' "
                + "ORDER BY id DESC LIMIT 1",
                nickname);
    }

    public void close() {
        try {
            this.executor.execute(new Runnable() {
                @Override public void run() { closeConnection(); }
            });
        } catch (RejectedExecutionException ignored) {
            return;
        }
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

    /* ------------------------------------------------------------------ */
    /*  Internals                                                         */
    /* ------------------------------------------------------------------ */

    @FunctionalInterface
    public interface SqlTask<T> {
        T run(Connection connection) throws SQLException;
    }

    private <T> CompletableFuture<T> submit(final SqlTask<T> task) {
        final CompletableFuture<T> future = new CompletableFuture<T>();
        try {
            this.executor.execute(new Runnable() {
                @Override public void run() {
                    try {
                        future.complete(runWithRetry(task));
                    } catch (Throwable t) {
                        future.completeExceptionally(t);
                    }
                }
            });
        } catch (RejectedExecutionException e) {
            future.completeExceptionally(e);
        }
        return future;
    }

    /** Runs the task; on failure closes the connection and retries once. */
    private <T> T runWithRetry(SqlTask<T> task) throws SQLException {
        try {
            return task.run(openConnection());
        } catch (Throwable first) {
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
                        if (rs.next()) {
                            return Optional.of(map(rs));
                        }
                        return Optional.<NickRecord>empty();
                    }
                }
            }
        });
    }

    /**
     * Returns a healthy JDBC connection.
     *
     * <p><b>Why not {@code Connection.isValid(int)}?</b> The SQLite driver
     * bundled with Spigot 1.8.8 ({@code org.sqlite.JDBC:3.7.2}) does not
     * implement that method. On Java 17 the JVM enforces the interface
     * contract and throws {@link AbstractMethodError}. We therefore probe
     * the connection with a trivial {@code SELECT 1} which every driver
     * since Java 6 supports.</p>
     */
    private Connection openConnection() throws SQLException {
        if (this.connection != null && !this.connection.isClosed()
                && probe(this.connection)) {
            return this.connection;
        }
        closeConnection();

        try {
            Class.forName(this.mysql
                    ? "com.mysql.cj.jdbc.Driver"
                    : "org.sqlite.JDBC");
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

    /** Portable liveness probe; never calls isValid(int). */
    private static boolean probe(Connection connection) {
        try (Statement s = connection.createStatement()) {
            s.execute("SELECT 1");
            return true;
        } catch (SQLException | AbstractMethodError e) {
            return false;
        }
    }

    private void closeConnection() {
        if (this.connection == null) return;
        try {
            this.connection.close();
        } catch (SQLException e) {
            this.plugin.getLogger().log(Level.WARNING,
                    "Failed to close database connection", e);
        } finally {
            this.connection = null;
        }
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

    private static String emptyIfNull(String value) {
        return value == null ? "" : value;
    }

    private static String setting(String key, String fallback) {
        String fromEnv = System.getenv(key);
        if (fromEnv != null && !fromEnv.trim().isEmpty()) {
            return fromEnv.trim();
        }
        return fallback == null ? "" : fallback;
    }

    private static int parsePort(String value) {
        try { return Integer.parseInt(value.trim()); }
        catch (NumberFormatException e) { return 3306; }
    }
}
'''


# ═══════════════════════════════════════════════════════════════════════════
#  pom.xml patcher
# ═══════════════════════════════════════════════════════════════════════════

SQLITE_DEP_BLOCK = """        <!-- Modern SQLite driver (compiled for Java 8) with a full JDBC 4
             implementation. Shaded under a private package so it never
             clashes with the 3.7.2 copy bundled inside Spigot 1.8.8. -->
        <dependency>
            <groupId>org.xerial</groupId>
            <artifactId>sqlite-jdbc</artifactId>
            <version>3.44.1.0</version>
            <scope>compile</scope>
        </dependency>
"""

SHADE_RELOCATION_BLOCK = """                            <relocations>
                                <relocation>
                                    <pattern>org.sqlite</pattern>
                                    <shadedPattern>com.yourname.nick.libs.sqlite</shadedPattern>
                                </relocation>
                            </relocations>
"""


def patch_pom(dry: bool, backup: bool) -> None:
    pom = ROOT / "pom.xml"
    if not pom.is_file():
        log("WARN", "pom.xml not found; skipping pom patch")
        return

    src = pom.read_text(encoding="utf-8")
    new = src
    changed = False

    # 1) Add the sqlite-jdbc dependency once.
    if "sqlite-jdbc" not in new:
        close_idx = new.rfind("</dependencies>")
        if close_idx < 0:
            log("WARN", "pom.xml has no </dependencies>; cannot add sqlite-jdbc")
        else:
            new = new[:close_idx] + SQLITE_DEP_BLOCK + new[close_idx:]
            changed = True

    # 2) Add the shade relocation once, right after createDependencyReducedPom.
    if "<relocations>" not in new:
        anchor = "<createDependencyReducedPom>false</createDependencyReducedPom>"
        anchor_idx = new.find(anchor)
        if anchor_idx < 0:
            log("WARN",
                "pom.xml has no shade plugin <createDependencyReducedPom>; "
                "cannot add relocation")
        else:
            insert_at = anchor_idx + len(anchor)
            new = new[:insert_at] + "\n" + SHADE_RELOCATION_BLOCK.rstrip() + new[insert_at:]
            changed = True

    if not changed:
        log("SKIP", "pom.xml already patched")
        return

    write_text(pom, new, dry=dry, backup=backup)


# ═══════════════════════════════════════════════════════════════════════════
#  Optional: patch the driver lookup inside StorageManager to prefer the
#  shaded class when it exists, otherwise fall back to org.sqlite.JDBC.
#  (Included here as a safeguard if the user re-runs the script after having
#  manually edited the file.)
# ═══════════════════════════════════════════════════════════════════════════

def patch_storage_driver_lookup(path: Path, dry: bool, backup: bool) -> None:
    if not path.is_file():
        return
    src = path.read_text(encoding="utf-8")
    if "libs.sqlite" in src or "org.sqlite.JDBC" in src and "ClassNotFound" in src:
        # Either the shaded class is already referenced, or the exact
        # fallback logic is already there.  Our verbatim write covers
        # this, so no surgical edit is needed.
        return
    # Not strictly needed because the verbatim rewrite always runs, but
    # we keep the hook so future edits are possible without replacing
    # the whole file.
    return


# ═══════════════════════════════════════════════════════════════════════════
#  Sentinel verification
# ═══════════════════════════════════════════════════════════════════════════

SENTINELS = {
    "storage/StorageManager.java": [
        "SELECT 1",                    # portable probe
        "runWithRetry",                # one-shot retry
        "PRAGMA journal_mode=WAL",
    ],
    "pom.xml": [
        "sqlite-jdbc",
        "<relocations>",
        "com.yourname.nick.libs.sqlite",
    ],
}


def verify_sentinels() -> bool:
    ok = True
    for rel, needles in SENTINELS.items():
        path = (ROOT / "src" / "main" / "java" / "com" / "yourname" / "nick" / rel) \
               if rel.endswith(".java") else (ROOT / rel)
        if not path.is_file():
            log("FAIL", f"missing {path.relative_to(ROOT)}")
            ok = False
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                log("FAIL", f"{path.relative_to(ROOT)} missing {needle!r}")
                ok = False
    return ok


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
            description="Fix SQLite AbstractMethodError in MineStormNickSystem.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    print("=" * 72)
    print("MineStormNickSystem - SQLite AbstractMethodError fixer")
    print(f"  project root : {ROOT}")
    print(f"  java package : {PACKAGE_DIR.relative_to(ROOT)}")
    print(f"  mode         : {'DRY-RUN' if args.dry_run else 'APPLY'}"
          f"{' (no backups)' if args.no_backup else ''}")
    print("=" * 72)
    print()

    if not (ROOT / "pom.xml").is_file():
        log("FATAL", f"pom.xml missing in {ROOT}")
        return 1

    backup = not args.no_backup

    # 1. Rewrite StorageManager.java with the portable version.
    storage_path = PACKAGE_DIR / "storage" / "StorageManager.java"
    write_text(storage_path, JAVA_STORAGE_MANAGER, dry=args.dry_run, backup=backup)

    # 2. Patch pom.xml (dependency + shade relocation).
    patch_pom(args.dry_run, backup)

    # 3. Verify.
    if not args.dry_run:
        print()
        log("CHK ", "verifying sentinels")
        if verify_sentinels():
            log("CHK ", "all sentinels present")
        else:
            log("CHK ", "some sentinels missing - see FAIL lines above")

    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    for level, message in LOG:
        print(f"  [{level:<4}] {message}")
    print()
    if args.dry_run:
        print("Dry-run complete. Re-run without --dry-run to apply.")
    else:
        print("Rebuild with:   mvn -B clean package")
        print("Then STOP the server fully and start it again (a /reload is not enough")
        print("because the old SQLite driver stays loaded in the JVM).")
    return 0


if __name__ == "__main__":
    sys.exit(main())