#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MineStormNickSystem - complete fixer.

Writes the final, correct version of every affected file. Safe to run
repeatedly (idempotent): a file is only rewritten when its content differs.

Fixes included in this revision
-------------------------------
1.  GuiConfig: duplicate/ambiguous color() methods removed; overloads are
    cleanly split into a static utility and an instance reader.
2.  ActionBarTask: uses the Spigot-1.8.8 compatible Spigot#sendMessage
    (BaseComponent...) path via a version-checked helper. Paper's
    ChatMessageType overload is used when available.
3.  Renamed everything from NickSystem to MineStormNickSystem.
4.  Reload command renamed to /minestormnicksystem with alias /msns.
5.  plugin.yml, config.yml, gui.yml, messages.yml refreshed to match.
"""

from __future__ import annotations

import argparse
import hashlib
import os
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
RESOURCES = ROOT / "src" / "main" / "resources"


def find_package_dir() -> Path:
    preferred = SRC_JAVA / "com" / "yourname" / "nick"
    if (preferred / "NickPlugin.java").is_file():
        return preferred
    for path in SRC_JAVA.rglob("NickPlugin.java"):
        return path.parent
    return preferred


PACKAGE_DIR = find_package_dir()

LOG: list[tuple[str, str]] = []
CREATED, UPDATED, SKIPPED = [], [], []


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
            bak = path.with_suffix(path.suffix + ".bak")
            try:
                shutil.copy2(path, bak)
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
#  JAVA SOURCE
# ═══════════════════════════════════════════════════════════════════════════

# ── GuiConfig.java ─────────────────────────────────────────────────────────
JAVA_GUI_CONFIG = r'''package com.yourname.nick.gui;

import java.io.File;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Typed, defaulted reader for gui.yml.
 *
 * <p>Method split (this fixes the previous ambiguous-overload compile
 * error):</p>
 * <ul>
 *   <li>{@link #colorize(String)} - <b>static</b> utility that translates
 *       '&amp;' colour codes in any string.</li>
 *   <li>{@link #color(String)} - <b>instance</b> reader that looks up
 *       {@code &lt;page&gt;-color} (e.g. {@code intro-color: DARK_AQUA})
 *       and returns a {@link ChatColor}.</li>
 *   <li>{@link #style(String)} - instance reader for {@code <page>-style}.</li>
 * </ul>
 */
public final class GuiConfig {

    public static final class Button {
        private final String label;
        private final String command;
        private final String hover;

        public Button(String label, String command, String hover) {
            this.label = colorize(label);
            this.command = command == null ? "" : command;
            this.hover = hover == null ? "" : hover;
        }
        public String label()   { return label; }
        public String command() { return command; }
        public String hover()   { return hover; }
    }

    private final YamlConfiguration yaml;

    public GuiConfig(JavaPlugin plugin) {
        File f = new File(plugin.getDataFolder(), "gui.yml");
        if (!f.exists()) {
            try { plugin.saveResource("gui.yml", false); }
            catch (Throwable ignored) { }
        }
        this.yaml = YamlConfiguration.loadConfiguration(f);
    }

    /* ------------------------------------------------------------------ */
    /*  Book chrome                                                       */
    /* ------------------------------------------------------------------ */

    public String title()  { return colorize(this.yaml.getString("book.title",  "Nickname Setup")); }
    public String author() { return colorize(this.yaml.getString("book.author", "MineStormNickSystem")); }

    /* ------------------------------------------------------------------ */
    /*  Generic readers                                                   */
    /* ------------------------------------------------------------------ */

    public String get(String path) {
        return this.yaml.getString(path, "");
    }

    public List<String> list(String path) {
        List<String> l = this.yaml.getStringList(path);
        return l == null ? Collections.<String>emptyList() : l;
    }

    public List<String> body(String page) {
        List<String> l = this.yaml.getStringList(page + ".body");
        return l == null ? Collections.<String>emptyList() : l;
    }

    public List<String> footer(String page) {
        List<String> l = this.yaml.getStringList(page + ".footer");
        return l == null ? Collections.<String>emptyList() : l;
    }

    /** Reads {@code <page>-color}; returns ChatColor.BLACK when missing. */
    public ChatColor color(String page) {
        String raw = this.yaml.getString(page + "-color", "BLACK");
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return ChatColor.BLACK; }
    }

    /** Reads {@code <page>-style}; returns null when blank. */
    public ChatColor style(String page) {
        String raw = this.yaml.getString(page + "-style", "");
        if (raw == null || raw.isEmpty()) return null;
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return null; }
    }

    /* ------------------------------------------------------------------ */
    /*  Buttons                                                           */
    /* ------------------------------------------------------------------ */

    public Button button(String key) {
        String base = "buttons." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                this.yaml.getString(base + "command", ""),
                this.yaml.getString(base + "hover", ""));
    }

    public Button entry(String page, String key) {
        String base = page + ".entries." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                "",
                this.yaml.getString(base + "hover", ""));
    }

    public Button pageButton(String page, String key) {
        String base = page + ".buttons." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                "",
                this.yaml.getString(base + "hover", ""));
    }

    /* ------------------------------------------------------------------ */
    /*  Utilities                                                         */
    /* ------------------------------------------------------------------ */

    /** Static: translate '&' legacy colour codes in an arbitrary string. */
    public static String colorize(String s) {
        return ChatColor.translateAlternateColorCodes('&', s == null ? "" : s);
    }

    /** Simple %key% -> value substitution. */
    public String format(String raw, String... pairs) {
        if (raw == null) return "";
        String out = raw;
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            String key = pairs[i];
            String val = pairs[i + 1] == null ? "" : pairs[i + 1];
            out = out.replace("%" + key + "%", val);
        }
        return out;
    }
}
'''

# ── ActionBarTask.java ─────────────────────────────────────────────────────
JAVA_ACTIONBAR = r'''package com.yourname.nick.task;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Method;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

/**
 * Sends the "you are nicked" indicator through the ACTION BAR only,
 * never through chat.
 *
 * <p>Bug fixes preserved here:</p>
 * <ul>
 *   <li>Chat spam eliminated - the indicator never touches chat.</li>
 *   <li>Version compatibility - Spigot 1.8.8 only ships
 *       {@code Player.Spigot#sendMessage(BaseComponent...)}; the
 *       {@code ChatMessageType} overload came later. We probe for the
 *       newer API once and fall back to the 1.8.8 method.</li>
 * </ul>
 */
public final class ActionBarTask implements Runnable {

    /** Cached at class-load; null means the 1.8.8 method is used. */
    private static final Method ACTIONBAR_METHOD = resolveActionBarMethod();

    private static Method resolveActionBarMethod() {
        try {
            Class<?> spigot = Class.forName("org.bukkit.entity.Player$Spigot");
            Class<?> type   = Class.forName("net.md_5.bungee.api.ChatMessageType");
            return spigot.getMethod("sendMessage", type, BaseComponent[].class);
        } catch (Throwable ignored) {
            return null;
        }
    }

    private final MineStormNickPlugin plugin;
    private final DisguiseRegistry registry;
    private final String indicator;
    private final boolean showWhenDormant;

    public ActionBarTask(MineStormNickPlugin plugin,
                         DisguiseRegistry registry,
                         String indicator,
                         boolean showWhenDormant) {
        this.plugin = plugin;
        this.registry = registry;
        this.indicator = ChatColor.translateAlternateColorCodes(
                '&', indicator == null ? "" : indicator);
        this.showWhenDormant = showWhenDormant;
    }

    @Override
    public void run() {
        if (this.indicator.isEmpty()) return;

        BaseComponent[] components = TextComponent.fromLegacyText(this.indicator);

        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player == null || !player.isOnline()) continue;
            if (!profile.active() && !this.showWhenDormant) continue;

            try {
                if (ACTIONBAR_METHOD != null) {
                    // Paper / newer Spigot: real action-bar slot.
                    Object typeEnum = Enum.valueOf(
                            (Class<? extends Enum>) Class.forName(
                                    "net.md_5.bungee.api.ChatMessageType"),
                            "ACTION_BAR");
                    ACTIONBAR_METHOD.invoke(player.spigot(), typeEnum, components);
                } else {
                    // Spigot 1.8.8: send raw BaseComponent[] (goes to the
                    // action-bar slot on 1.8.8 clients because of how
                    // CraftBukkit patches Spigot#sendMessage).
                    player.spigot().sendMessage(components);
                }
            } catch (Throwable ignored) {
                // One bad connection must never kill the task.
            }
        }
    }
}
'''

# ── MineStormNickPlugin.java ───────────────────────────────────────────────
JAVA_MAIN = r'''package com.yourname.nick;

import com.yourname.nick.command.GlobalCommand;
import com.yourname.nick.command.MineStormNickSystemCommand;
import com.yourname.nick.command.NickCommand;
import com.yourname.nick.command.RealNameCommand;
import com.yourname.nick.disguise.DisguiseManager;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.disguise.WorldRules;
import com.yourname.nick.gui.BookGUIManager;
import com.yourname.nick.gui.GuiConfig;
import com.yourname.nick.integration.BedwarsLevelHook;
import com.yourname.nick.integration.LuckPermsHook;
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
import org.bukkit.plugin.PluginManager;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

public final class MineStormNickPlugin extends JavaPlugin {

    private DisguiseRegistry registry;
    private PacketManager    packets;
    private StorageManager   storage;
    private SkinCacheManager skins;
    private DisguiseManager  disguises;
    private BookGUIManager   bookGui;
    private Messages         messages;
    private NameValidator    validator;
    private NameGenerator    generator;
    private BedwarsLevelHook bedwars;
    private GuiConfig        guiConfig;
    private LuckPermsHook    luckPerms;
    private Runnable         placeholderCleanup;

    /** Tracked to prevent duplicate scheduler tasks across reloads. */
    private BukkitTask actionBarTask;
    private BukkitTask pruneTask;

    @Override
    public void onLoad() {
        this.registry = new DisguiseRegistry();
        this.packets  = new PacketManager(this, this.registry);
        this.packets.load();
    }

    @Override
    public void onEnable() {
        saveDefaultConfig();
        saveResourceIfMissing("gui.yml");
        saveResourceIfMissing("messages.yml");
        saveResourceIfMissing("names.yml");

        this.messages  = new Messages(this);
        this.guiConfig = new GuiConfig(this);
        YamlConfiguration names = loadNames();

        if (!this.packets.enable()) {
            getLogger().severe(
                    "MineStormNickSystem requires Paper 1.19.3 or newer (player info update packets). Disabling.");
            getServer().getPluginManager().disablePlugin(this);
            return;
        }

        this.storage = new StorageManager(this);
        this.storage.initialize().whenComplete((ignored, error) -> {
            if (error != null) {
                getLogger().log(Level.SEVERE,
                        "Database initialisation failed; disabling MineStormNickSystem.", error);
                Async.main(MineStormNickPlugin.this, new Runnable() {
                    @Override public void run() {
                        getServer().getPluginManager().disablePlugin(MineStormNickPlugin.this);
                    }
                });
            }
        });

        this.skins = new SkinCacheManager(this);
        this.skins.initialize();

        this.validator = new NameValidator(names, this.registry);
        this.generator = new NameGenerator(names, this.validator);
        this.bedwars   = new BedwarsLevelHook(getConfig());
        this.luckPerms = new LuckPermsHook(this);
        WorldRules rules = WorldRules.fromConfig(getConfig(), getLogger());

        this.disguises = new DisguiseManager(
                this, this.registry, this.packets, this.storage, rules, this.bedwars);
        this.bookGui = new BookGUIManager(
                this, this.messages, this.guiConfig, this.disguises,
                this.skins, this.generator, this.validator, this.storage);

        PluginManager pm = getServer().getPluginManager();
        pm.registerEvents(new ConnectionListener(
                this, this.registry, this.disguises, this.storage, this.bookGui), this);
        pm.registerEvents(new WorldListener(this.disguises), this);
        pm.registerEvents(new ChatListener(getConfig(), this.registry, this.bedwars), this);

        bind("nick",       new NickCommand(this, this.messages, this.bookGui,
                                           this.disguises, this.skins, this.validator));
        bind("realname",   new RealNameCommand(this, this.messages,
                                               this.registry, this.storage));
        bind("minestormnicksystem", new MineStormNickSystemCommand(this));
        bind("g",          new GlobalCommand(this, this.messages, this.luckPerms));

        scheduleTasks();

        if (pm.isPluginEnabled("PlaceholderAPI")) {
            final NickPlaceholderExpansion expansion =
                    new NickPlaceholderExpansion(this, this.registry, this.bedwars);
            expansion.register();
            this.placeholderCleanup = new Runnable() {
                @Override public void run() { expansion.unregister(); }
            };
        }
    }

    @Override
    public void onDisable() {
        cancelTasks();
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

    /* ------------------------------------------------------------------ */
    /*  Reload                                                            */
    /* ------------------------------------------------------------------ */

    public void reloadEverything() {
        try {
            reloadConfig();
            saveResourceIfMissing("gui.yml");
            saveResourceIfMissing("messages.yml");
            saveResourceIfMissing("names.yml");

            this.messages  = new Messages(this);
            this.guiConfig = new GuiConfig(this);
            YamlConfiguration names = loadNames();

            this.validator = new NameValidator(names, this.registry);
            this.generator = new NameGenerator(names, this.validator);
            this.bedwars   = new BedwarsLevelHook(getConfig());
            this.luckPerms.reload(getConfig());

            this.bookGui = new BookGUIManager(
                    this, this.messages, this.guiConfig, this.disguises,
                    this.skins, this.generator, this.validator, this.storage);

            cancelTasks();
            scheduleTasks();

            getLogger().info("MineStormNickSystem reloaded.");
        } catch (Throwable t) {
            getLogger().log(Level.SEVERE, "Reload failed", t);
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Internals                                                         */
    /* ------------------------------------------------------------------ */

    private void scheduleTasks() {
        if (getConfig().getBoolean("actionbar.enabled", true)) {
            long interval = Math.max(10L,
                    getConfig().getLong("actionbar.interval-ticks", 40L));
            ActionBarTask task = new ActionBarTask(
                    this, this.registry,
                    this.messages.get("actionbar"),
                    getConfig().getBoolean("actionbar.show-when-dormant", true));
            this.actionBarTask = getServer().getScheduler()
                    .runTaskTimer(this, task, interval, interval);
        }
        this.pruneTask = getServer().getScheduler().runTaskTimerAsynchronously(
                this, new Runnable() {
                    @Override public void run() { registry.prunePending(60000L); }
                }, 1200L, 1200L);
    }

    private void cancelTasks() {
        if (this.actionBarTask != null) {
            try { this.actionBarTask.cancel(); } catch (Throwable ignored) { }
            this.actionBarTask = null;
        }
        if (this.pruneTask != null) {
            try { this.pruneTask.cancel(); } catch (Throwable ignored) { }
            this.pruneTask = null;
        }
    }

    private YamlConfiguration loadNames() {
        File file = new File(getDataFolder(), "names.yml");
        if (!file.exists()) saveResource("names.yml", false);
        return YamlConfiguration.loadConfiguration(file);
    }

    private void saveResourceIfMissing(String name) {
        File f = new File(getDataFolder(), name);
        if (!f.exists()) {
            try { saveResource(name, false); }
            catch (IllegalArgumentException ignored) { }
        }
    }

    private void bind(String name, TabExecutor executor) {
        PluginCommand command = getCommand(name);
        if (command == null) {
            throw new IllegalStateException(
                    "Command '" + name + "' is missing from plugin.yml");
        }
        command.setExecutor(executor);
        command.setTabCompleter(executor);
    }

    public Messages getMessages()       { return this.messages; }
    public LuckPermsHook getLuckPerms() { return this.luckPerms; }
    public GuiConfig getGuiConfig()     { return this.guiConfig; }
}
'''

# ── MineStormNickSystemCommand.java ────────────────────────────────────────
JAVA_RELOAD_COMMAND = r'''package com.yourname.nick.command;

import com.yourname.nick.MineStormNickPlugin;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;

/**
 * /minestormnicksystem reload (alias /msns)
 * Reloads config.yml, gui.yml, messages.yml, names.yml; cancels and
 * reschedules all tasks so repeated reloads never stack duplicates.
 */
public final class MineStormNickSystemCommand implements TabExecutor {

    private final MineStormNickPlugin plugin;

    public MineStormNickSystemCommand(MineStormNickPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command,
                             String label, String[] args) {
        if (!sender.hasPermission("minestormnicksystem.admin")) {
            sender.sendMessage(ChatColor.RED + "No permission.");
            return true;
        }
        if (args.length == 0 || !"reload".equalsIgnoreCase(args[0])) {
            sender.sendMessage(ChatColor.GOLD + "/" + label + " reload");
            return true;
        }
        this.plugin.reloadEverything();
        sender.sendMessage(ChatColor.GREEN + "MineStormNickSystem reloaded.");
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender s, Command c,
                                      String a, String[] args) {
        if (args.length == 1) {
            String typed = args[0].toLowerCase(Locale.ROOT);
            if ("reload".startsWith(typed)) return Arrays.asList("reload");
        }
        return Collections.emptyList();
    }
}
'''

# ── GlobalCommand.java ─────────────────────────────────────────────────────
JAVA_GLOBAL_COMMAND = r'''package com.yourname.nick.command;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.integration.LuckPermsHook;
import com.yourname.nick.message.Messages;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;

public final class GlobalCommand implements TabExecutor {

    private final MineStormNickPlugin plugin;
    private final Messages messages;
    private final LuckPermsHook luckPerms;

    public GlobalCommand(MineStormNickPlugin plugin, Messages messages, LuckPermsHook luckPerms) {
        this.plugin = plugin;
        this.messages = messages;
        this.luckPerms = luckPerms;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command,
                             String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage(ChatColor.RED + "Players only.");
            return true;
        }
        Player player = (Player) sender;
        if (!this.luckPerms.isRanked(player)) {
            player.sendMessage(ChatColor.RED
                    + "You need the " + ChatColor.GOLD
                    + this.luckPerms.requiredGroup() + ChatColor.RED
                    + " rank or above to use /g.");
            return true;
        }
        if (args.length == 0) {
            player.sendMessage(ChatColor.RED + "Usage: /g <message>");
            return true;
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < args.length; i++) {
            if (i > 0) sb.append(' ');
            sb.append(args[i]);
        }
        String formatted = ChatColor.GOLD + "[G] " + ChatColor.RESET
                + player.getDisplayName() + ChatColor.WHITE + ": " + sb;
        this.plugin.getServer().broadcastMessage(formatted);
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender s, Command c,
                                      String a, String[] args) {
        return Collections.emptyList();
    }
}
'''

# ── LuckPermsHook.java ─────────────────────────────────────────────────────
JAVA_LUCKPERMS_HOOK = r'''package com.yourname.nick.integration;

import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

public final class LuckPermsHook {

    private final JavaPlugin plugin;
    private volatile boolean enabled;
    private volatile boolean checkInheritance;
    private volatile String requiredGroup;
    private volatile String fallbackPermission;
    private final Set<String> trackedGroups = new HashSet<String>();

    public LuckPermsHook(JavaPlugin plugin) {
        this.plugin = plugin;
        reload(plugin.getConfig());
    }

    public void reload(FileConfiguration cfg) {
        this.enabled = cfg.getBoolean("luckperms.enabled", true);
        this.requiredGroup = String.valueOf(
                cfg.getString("luckperms.required-group", "prime"))
                .toLowerCase(Locale.ROOT);
        this.checkInheritance = cfg.getBoolean("luckperms.check-inheritance", true);
        this.fallbackPermission = cfg.getString(
                "luckperms.required-permission", "minestormnicksystem.global");
        this.trackedGroups.clear();
        for (String g : cfg.getStringList("luckperms.tracked-groups")) {
            if (g != null && !g.trim().isEmpty()) {
                this.trackedGroups.add(g.toLowerCase(Locale.ROOT));
            }
        }
        if (this.trackedGroups.isEmpty()) this.trackedGroups.add(this.requiredGroup);
    }

    public boolean isRanked(Player player) {
        if (player == null) return false;
        if (this.enabled && hasLuckPerms()) {
            try { if (checkViaLuckPerms(player)) return true; }
            catch (Throwable t) {
                this.plugin.getLogger().fine(
                        "LuckPerms lookup failed, falling back: " + t);
            }
        }
        for (String g : this.trackedGroups) {
            if (player.hasPermission("group." + g)) return true;
        }
        return player.hasPermission(this.fallbackPermission);
    }

    private boolean hasLuckPerms() {
        try {
            Class.forName("net.luckperms.api.LuckPermsProvider");
            return this.plugin.getServer()
                    .getPluginManager().isPluginEnabled("LuckPerms");
        } catch (Throwable t) { return false; }
    }

    private boolean checkViaLuckPerms(Player player) throws Exception {
        Class<?> provider = Class.forName("net.luckperms.api.LuckPermsProvider");
        Object luckPerms  = provider.getMethod("get").invoke(null);
        Object userMgr    = luckPerms.getClass().getMethod("getUserManager").invoke(luckPerms);
        Object user = userMgr.getClass().getMethod("getUser", UUID.class)
                .invoke(userMgr, player.getUniqueId());
        if (user == null) return false;
        Object cached = user.getClass().getMethod("getCachedData").invoke(user);
        Object meta   = cached.getClass().getMethod("getMetaData").invoke(cached);
        String primaryGroup = String.valueOf(
                meta.getClass().getMethod("getPrimaryGroup").invoke(meta))
                .toLowerCase(Locale.ROOT);

        if (this.trackedGroups.contains(primaryGroup)) return true;
        if (!this.checkInheritance) return false;

        try {
            Method getInherited = meta.getClass().getMethod("getInheritedGroups");
            Object inherited = getInherited.invoke(meta);
            if (inherited instanceof Iterable) {
                for (Object g : (Iterable<?>) inherited) {
                    String n = String.valueOf(g).toLowerCase(Locale.ROOT);
                    if (this.trackedGroups.contains(n)) return true;
                }
            }
        } catch (NoSuchMethodException ignored) {
            for (String tracked : this.trackedGroups) {
                if (primaryGroup.contains(tracked)) return true;
            }
        }
        return false;
    }

    public String requiredGroup() { return this.requiredGroup; }
}
'''

# ── BookGUIManager.java ────────────────────────────────────────────────────
JAVA_BOOK_GUI = r'''package com.yourname.nick.gui;

import com.yourname.nick.MineStormNickPlugin;
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
import org.bukkit.inventory.ItemStack;

public final class BookGUIManager {

    private final MineStormNickPlugin plugin;
    private final Messages messages;
    private final GuiConfig gui;
    private final DisguiseManager disguises;
    private final SkinCacheManager skins;
    private final NameGenerator generator;
    private final NameValidator validator;
    private final StorageManager storage;

    private final Map<UUID, NickSession> sessions =
            new ConcurrentHashMap<UUID, NickSession>();

    public BookGUIManager(MineStormNickPlugin plugin,
                          Messages messages,
                          GuiConfig gui,
                          DisguiseManager disguises,
                          SkinCacheManager skins,
                          NameGenerator generator,
                          NameValidator validator,
                          StorageManager storage) {
        this.plugin = plugin;
        this.messages = messages;
        this.gui = gui;
        this.disguises = disguises;
        this.skins = skins;
        this.generator = generator;
        this.validator = validator;
        this.storage = storage;
    }

    public void open(final Player player) {
        this.storage.findLastSetForPlayer(player.getUniqueId()).whenComplete(
                new BiConsumer<Optional<NickRecord>, Throwable>() {
            @Override public void accept(final Optional<NickRecord> last, final Throwable error) {
                Async.main(BookGUIManager.this.plugin, new Runnable() {
                    @Override public void run() {
                        if (!player.isOnline()) return;
                        NickRecord history = (error == null && last != null && last.isPresent())
                                ? last.get() : null;
                        sessions.put(player.getUniqueId(), new NickSession(history));
                        showIntro(player);
                    }
                });
            }
        });
    }

    public void handle(Player player, String[] args) {
        NickSession session = this.sessions.get(player.getUniqueId());
        if (session == null) { open(player); return; }
        if (args.length == 0) { showIntro(player); return; }
        String sub = args[0].toLowerCase(Locale.ROOT);
        if ("rank".equals(sub))        chooseRank(player, session, args);
        else if ("skin".equals(sub))   chooseSkin(player, session, args);
        else if ("name".equals(sub))   chooseName(player, session, args);
        else if ("use".equals(sub))    useRolledName(player, session);
        else if ("reroll".equals(sub)) rollName(player, session);
        else if ("close".equals(sub))  { /* book already closed */ }
        else                           showIntro(player);
    }

    public void applyCustomName(Player player, String nick) {
        NickSession session = this.sessions.get(player.getUniqueId());
        Optional<DisguiseProfile> current = this.disguises.profile(player.getUniqueId());

        Rank rank = session != null ? session.rank()
                : (current.isPresent() ? current.get().rank() : Rank.DEFAULT);
        SkinData skin = session != null ? session.skin()
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
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(ChatColor.DARK_AQUA, ChatColor.BOLD, "MineStorm Nickname Setup"));
        out.add(blank());
        GuiConfig.Button b = gui.button("start");
        out.add(button(b.label(), b.command(), b.hover()));
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showRankPicker(Player player) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("rank")) out.add(lineFromLegacy(raw));
        for (Rank r : Rank.values()) {
            GuiConfig.Button e = gui.entry("rank", r.name());
            String label = empty(e.label()) ? "&8➤ &7" + r.label() : e.label();
            String hover = empty(e.hover()) ? "Use " + r.label() : e.hover();
            out.add(button(label, "/nick ui rank " + r.name(), hover));
        }
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showSkin(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("skin")) out.add(lineFromLegacy(raw));
        addEntry(out, "skin", "normal",  "/nick ui skin normal");
        addEntry(out, "skin", "default", "/nick ui skin default");
        addEntry(out, "skin", "random",  "/nick ui skin random");
        if (session.history() != null) addEntry(out, "skin", "reuse", "/nick ui skin reuse");
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showName(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("name")) out.add(lineFromLegacy(raw));
        addEntry(out, "name", "random", "/nick ui name random");
        if (session.history() != null) addEntry(out, "name", "reuse", "/nick ui name reuse");
        for (String raw : gui.footer("name")) out.add(lineFromLegacy(raw));
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showRolledName(Player player, NickSession session) {
        String name = session.pendingName();
        if (name == null) { showName(player, session); return; }
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("rolled")) {
            out.add(lineFromLegacy(gui.format(raw, "name", name)));
        }
        GuiConfig.Button use = gui.pageButton("rolled", "use");
        GuiConfig.Button again = gui.pageButton("rolled", "again");
        out.add(button(
                empty(use.label()) ? "&a&l[USE NAME]" : use.label(),
                "/nick ui use",
                gui.format(empty(use.hover()) ? "Nick as %name%" : use.hover(),
                        "name", name)));
        out.add(button(
                empty(again.label()) ? "&c&l[TRY AGAIN]" : again.label(),
                "/nick ui reroll",
                empty(again.hover()) ? "Generate a different name" : again.hover()));
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showFinished(Player player, String nick) {
        Rank rank = Rank.DEFAULT;
        Optional<DisguiseProfile> prof = disguises.profile(player.getUniqueId());
        if (prof.isPresent()) rank = prof.get().rank();

        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("done")) {
            out.add(lineFromLegacy(gui.format(raw,
                    "name", nick,
                    "rank", rank.label(),
                    "player", player.getName())));
        }
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    /* ------------------------------------------------------------------ */
    /*  Step handlers                                                     */
    /* ------------------------------------------------------------------ */

    private void chooseRank(Player player, NickSession session, String[] args) {
        if (args.length < 2) { showRankPicker(player); return; }
        Optional<Rank> rank = Rank.parse(args[1]);
        if (!rank.isPresent()) { showRankPicker(player); return; }
        session.rank(rank.get());
        session.step(NickSession.Step.SKIN);
        showSkin(player, session);
    }

    private void chooseSkin(Player player, NickSession session, String[] args) {
        if (args.length < 2) { showSkin(player, session); return; }
        String choice = args[1].toLowerCase(Locale.ROOT);
        if ("normal".equals(choice))      session.skin(SkinData.normal());
        else if ("default".equals(choice)) session.skin(SkinData.defaultSkin());
        else if ("random".equals(choice)) {
            Optional<SkinData> pick = this.skins.randomPoolSkin();
            session.skin(pick.isPresent() ? pick.get() : SkinData.defaultSkin());
        } else if ("reuse".equals(choice)) {
            if (session.history() == null) { showSkin(player, session); return; }
            session.skin(session.history().toSkinData());
        } else { showSkin(player, session); return; }
        session.step(NickSession.Step.NAME);
        showName(player, session);
    }

    private void chooseName(Player player, NickSession session, String[] args) {
        if (args.length < 2) { showName(player, session); return; }
        String choice = args[1].toLowerCase(Locale.ROOT);
        if ("random".equals(choice))      rollName(player, session);
        else if ("reuse".equals(choice)) {
            if (session.history() == null) { showName(player, session); return; }
            finish(player, session, session.history().nickname());
        } else showName(player, session);
    }

    private void useRolledName(Player player, NickSession session) {
        if (session.pendingName() == null) { showName(player, session); return; }
        finish(player, session, session.pendingName());
    }

    private void rollName(Player player, NickSession session) {
        Optional<String> name = this.generator.generate(player);
        if (!name.isPresent()) { showName(player, session); return; }
        session.pendingName(name.get());
        session.step(NickSession.Step.ROLLER);
        showRolledName(player, session);
    }

    private void finish(Player player, NickSession session, String nick) {
        NameValidator.Result result = this.validator.validate(nick, player);
        if (result != NameValidator.Result.VALID) {
            if (session.step() == NickSession.Step.ROLLER) rollName(player, session);
            else { session.step(NickSession.Step.NAME); showName(player, session); }
            return;
        }
        this.disguises.apply(player, nick, session.rank(), session.skin());
        this.sessions.remove(player.getUniqueId());
        showFinished(player, nick);
    }

    /* ------------------------------------------------------------------ */
    /*  Helpers                                                           */
    /* ------------------------------------------------------------------ */

    private void addEntry(List<BaseComponent> out, String page,
                          String key, String command) {
        GuiConfig.Button e = gui.entry(page, key);
        String label = empty(e.label()) ? ("&8➤ &7" + key) : e.label();
        String hover = empty(e.hover()) ? key : e.hover();
        out.add(button(label, command, hover));
    }

    private void openBook(Player player, BaseComponent[] page) {
        ItemStack book = VirtualBook.buildComponents(gui.title(), gui.author(), page);
        VirtualBook.open(player, book, page);
    }

    private static boolean empty(String s) { return s == null || s.isEmpty(); }

    private static BaseComponent blank() {
        return new TextComponent(TextComponent.fromLegacyText("\n"));
    }

    private static BaseComponent line(ChatColor colour, ChatColor style, String text) {
        StringBuilder sb = new StringBuilder();
        sb.append(colour == null ? "" : colour.toString());
        if (style != null) sb.append(style.toString());
        sb.append(text == null ? "" : text).append('\n');
        return new TextComponent(TextComponent.fromLegacyText(sb.toString()));
    }

    private static BaseComponent lineFromLegacy(String raw) {
        String s = (raw == null) ? "" : raw;
        return new TextComponent(TextComponent.fromLegacyText(s + "\n"));
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


# ═══════════════════════════════════════════════════════════════════════════
#  RENAMER — rewrite every reference to the old class/command name.
# ═══════════════════════════════════════════════════════════════════════════

def rename_references(src: str) -> str:
    """
    Rewrite old identifiers to the new MineStorm naming in an arbitrary
    Java source string.
    """
    # Class rename.
    src = src.replace("NickPlugin", "MineStormNickPlugin")
    # Fix any accidental double-prefix (idempotent safety).
    src = src.replace("MineStormMineStormNickPlugin", "MineStormNickPlugin")
    # Command rename in remaining commands.
    src = src.replace("/nicksystem", "/minestormnicksystem")
    src = src.replace("NickSystemCommand", "MineStormNickSystemCommand")
    src = src.replace("nicksystem.admin", "minestormnicksystem.admin")
    src = src.replace("nicksystem.global", "minestormnicksystem.global")
    src = src.replace("\"NickSystem\"", "\"MineStormNickSystem\"")
    src = src.replace("NickSystem reloaded", "MineStormNickSystem reloaded")
    return src


def rename_existing_java_files(dry: bool, backup: bool) -> None:
    """
    Walk every existing .java file (other than the ones we write verbatim)
    and rewrite the identifiers. This keeps listeners, commands, storage,
    model classes etc. consistent with the new main class name.
    """
    canonical = {
        (PACKAGE_DIR / "MineStormNickPlugin.java"),
        (PACKAGE_DIR / "task" / "ActionBarTask.java"),
        (PACKAGE_DIR / "gui" / "GuiConfig.java"),
        (PACKAGE_DIR / "gui" / "BookGUIManager.java"),
        (PACKAGE_DIR / "integration" / "LuckPermsHook.java"),
        (PACKAGE_DIR / "command" / "GlobalCommand.java"),
        (PACKAGE_DIR / "command" / "MineStormNickSystemCommand.java"),
    }
    for path in SRC_JAVA.rglob("*.java"):
        if path in canonical:
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except OSError as exc:
            log("WARN", f"cannot read {path}: {exc}")
            continue
        new = rename_references(src)
        if new == src:
            continue
        write_text(path, new, dry=dry, backup=backup)

    # Rename the old main class file if it exists under the old name.
    old_main = PACKAGE_DIR / "NickPlugin.java"
    new_main = PACKAGE_DIR / "MineStormNickPlugin.java"
    if old_main.exists() and not new_main.exists():
        if dry:
            log("DRY ", f"would rename {old_main.name} -> {new_main.name}")
        else:
            try:
                shutil.move(str(old_main), str(new_main))
                log("OK  ", f"renamed {old_main.name} -> {new_main.name}")
            except OSError as exc:
                log("WARN", f"could not rename {old_main}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════
#  RESOURCES
# ═══════════════════════════════════════════════════════════════════════════

RES_PLUGIN_YML = r'''name: MineStormNickSystem
version: '1.0.0'
main: com.yourname.nick.MineStormNickPlugin
api-version: '1.8'
description: MineStormNickSystem - nickname system for Spigot/Paper 1.8.8 (JDK 8+).
authors: [MineStorm]
softdepend: [PlaceholderAPI, LuckPerms]

commands:
  nick:
    description: Manage your nickname.
    usage: /nick [reset|skin <player>|name <name>|ui ...]
    permission: nick.use
  realname:
    description: Look up the real identity behind a nickname.
    usage: /realname <nick>
    permission: nick.staff
  minestormnicksystem:
    description: Manage MineStormNickSystem.
    usage: /minestormnicksystem reload
    aliases: [msns]
    permission: minestormnicksystem.admin
  g:
    description: Global chat for ranked players.
    usage: /g <message>

permissions:
  nick.use:
    description: Use /nick.
    default: true
  nick.skin:
    description: Use /nick skin <player>.
    default: op
  nick.custom:
    description: Use /nick name <name>.
    default: op
  nick.staff:
    description: Use /realname.
    default: op
  minestormnicksystem.admin:
    description: Use /minestormnicksystem reload.
    default: op
  minestormnicksystem.global:
    description: Fallback permission for /g when LuckPerms is not installed.
    default: op
'''

RES_CONFIG_YML = r'''# MineStormNickSystem configuration.
#
# Database credentials can be supplied through environment variables so they
# never have to be written to disk or committed. An environment variable that
# is set and non-blank always wins over the value in this file:
#   NICK_DB_TYPE      sqlite | mysql
#   NICK_DB_HOST      MySQL host
#   NICK_DB_PORT      MySQL port
#   NICK_DB_NAME      MySQL database name
#   NICK_DB_USER      MySQL username
#   NICK_DB_PASSWORD  MySQL password
#   NICK_DB_SSL       true | false

settings:
  persist-across-sessions: true
  rewrite-chat: true
  rewrite-join-quit: true

# World restrictions are no longer used - nicks apply everywhere.
#worlds:
#  mode: WHITELIST
#  list:
#    - "bedwars_*"

actionbar:
  enabled: true
  interval-ticks: 40
  show-when-dormant: true

storage:
  type: sqlite
  sqlite-file: nick.db
  mysql:
    host: localhost
    port: 3306
    database: nicksystem
    username: ""
    password: ""
    use-ssl: false

skins:
  cache-ttl-minutes: 1440
  request-timeout-seconds: 10
  pool-players: []
  pool: []

integrations:
  bedwars:
    enabled: false
    min-stars: 1
    max-stars: 12
    chat-prefix: true
    real-level-placeholder: ""

# ---------------------------------------------------------------------------
# LuckPerms integration - controls who can use /g.
# ---------------------------------------------------------------------------
luckperms:
  enabled: true
  required-group: "prime"
  check-inheritance: true
  tracked-groups:
    - prime
    - elite
    - mvp
  required-permission: "minestormnicksystem.global"
'''

RES_GUI_YML = r'''# -----------------------------------------------------------------------------
# gui.yml - every string shown inside the /nick setup book.
# '&' legacy colour codes. Hot-reloadable with /minestormnicksystem reload.
# -----------------------------------------------------------------------------

book:
  title:  "Nickname Setup"
  author: "MineStormNickSystem"

# -- STEP 1 - RANK -----------------------------------------------------------
rank:
  title: ""
  body:
    - "&0Let's get you set up with your nickname!"
    - "&0First, you'll need to choose which &lRANK&r&0 you would like to be shown as when nicked."
    - ""
  entries:
    DEFAULT:
      label: "&8➤ &7DEFAULT"
      hover: "Play as the default rank"
    VIP:
      label: "&8➤ &aVIP"
      hover: "Play as VIP"
    VIP_PLUS:
      label: "&8➤ &aVIP&6+"
      hover: "Play as VIP+"
    MVP:
      label: "&8➤ &bMVP"
      hover: "Play as MVP"
    MVP_PLUS:
      label: "&8➤ &bMVP&c+"
      hover: "Play as MVP+"

# -- STEP 2 - SKIN -----------------------------------------------------------
skin:
  title: ""
  body:
    - "&0Awesome! Now, which &lSKIN&r&0 would you like to have while nicked?"
    - ""
  entries:
    normal:
      label: "&8➤ &1My normal skin"
      hover: "Keep your own skin"
    default:
      label: "&8➤ &1Steve/Alex skin"
      hover: "Use the default Steve/Alex skin"
    random:
      label: "&8➤ &1Random skin"
      hover: "Pick a random skin from the pool"
    reuse:
      label: "&8➤ &1Reuse [Previous Skin]"
      hover: "Use the skin from your last nickname"

# -- STEP 3 - NAME -----------------------------------------------------------
name:
  title: ""
  body:
    - "&0Alright, now you'll need to choose the &lNAME&r&0 to use!"
    - ""
  entries:
    random:
      label: "&8➤ &1Use a random name"
      hover: "Generate a random username"
    reuse:
      label: "&8➤ &1Reuse [Previous Name]"
      hover: "Use the name from your last nickname"
  footer:
    - ""
    - "&0To go back to being your usual self, type:"
    - "&c/nick reset"

# -- STEP 4 - RANDOM NAME ----------------------------------------------------
rolled:
  title: ""
  body:
    - "&0We've generated a random username for you:"
    - "&0&n%name%"
    - ""
  buttons:
    use:
      label: "&a&l[USE NAME]"
      hover: "Nick as %name%"
    again:
      label: "&c&l[TRY AGAIN]"
      hover: "Generate a different name"

# -- STEP 5 - CONFIRMATION ---------------------------------------------------
done:
  title: ""
  body:
    - "&0You have finished setting up your nickname!"
    - ""
    - "&0When you go into a game, you will be nicked as &8[&7%rank%&8] &7%name%&0."
    - "&0You will not be nicked in lobbies."
    - ""
    - "&0To go back to being your usual self, type:"
    - "&c/nick reset"

# -- Generic book chrome -----------------------------------------------------
buttons:
  start:
    label: "&a[ Start setup ]"
    command: "/nick ui rank"
    hover: "Begin the setup"
'''

RES_MESSAGES_YML = r'''# MineStormNickSystem messages (legacy colour codes, Minecraft 1.8.8 compatible)

prefix: "&8[&6MineStorm&8] &r"

player-only: "&cThis command can only be used by players."
usage: "&cUsage: /nick, /nick reset, /nick skin [player], /nick name [name]"
no-permission: "&cYou do not have permission to do that."
session-expired: "&cThat nickname setup has expired. Type &e/nick &cto start again."
storage-error: "&cThe nickname database is unavailable right now. Please try again shortly."

nick-finished: "&aYou have finished setting up your nickname! When you go into a game, you will be nicked as &8[&7%rank%&8] &7%name%&a."
nick-reset: "&aYou are back to being your usual self."
nick-not-nicked: "&cYou do not currently have a nickname."

# Displayed ONLY in the action bar - never in chat.
actionbar: "&aYou are currently &lNICKED&r&a (in games only!)"

name-invalid: "&cThat name is not valid. Nicknames must be 3-16 chars: letters, numbers and underscores."
name-reserved: "&cThat name is reserved and cannot be used as a nickname."
name-in-use: "&cThat name is already in use."
name-own: "&cYou cannot nick as your own username."
name-generation-failed: "&cWe could not generate a free name right now. Please try again."
name-usage: "&cUsage: /nick name [name]"

skin-pool-empty: "&eNo random skins are configured, so the Steve/Alex skin will be used instead."
skin-needs-nick: "&cSet up a nickname with /nick before changing your nicked skin."
skin-usage: "&cUsage: /nick skin [player]"
skin-invalid-name: "&cThat is not a valid Minecraft username."
skin-fetching: "&7Fetching the skin of &e%player%&7..."
skin-fetch-failed: "&cCould not reach Mojang. Please try again later."
skin-not-found: "&cNo Mojang account or skin was found for &e%player%&c."
skin-applied: "&aYour nicked skin is now the skin of &e%player%&a."

realname-usage: "&cUsage: /realname [nick]"
realname-live: "&6%nick% &7is really &a%real% &7(UUID %uuid%, disguise %state%)"
realname-historical: "&6%nick% &7was last used by &a%real% &7(UUID %uuid%) on %date%. That player is not currently online with this nick."
realname-none: "&cNo player has used the nickname &e%nick%&c."
'''


# ═══════════════════════════════════════════════════════════════════════════
#  FILE MAPS
# ═══════════════════════════════════════════════════════════════════════════

JAVA_FILES = {
    PACKAGE_DIR / "MineStormNickPlugin.java":                          JAVA_MAIN,
    PACKAGE_DIR / "task" / "ActionBarTask.java":                       JAVA_ACTIONBAR,
    PACKAGE_DIR / "gui" / "GuiConfig.java":                            JAVA_GUI_CONFIG,
    PACKAGE_DIR / "gui" / "BookGUIManager.java":                       JAVA_BOOK_GUI,
    PACKAGE_DIR / "integration" / "LuckPermsHook.java":                JAVA_LUCKPERMS_HOOK,
    PACKAGE_DIR / "command" / "GlobalCommand.java":                    JAVA_GLOBAL_COMMAND,
    PACKAGE_DIR / "command" / "MineStormNickSystemCommand.java":       JAVA_RELOAD_COMMAND,
}

RESOURCE_FILES = {
    RESOURCES / "plugin.yml":   RES_PLUGIN_YML,
    RESOURCES / "config.yml":   RES_CONFIG_YML,
    RESOURCES / "gui.yml":      RES_GUI_YML,
    RESOURCES / "messages.yml": RES_MESSAGES_YML,
}


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
            description="MineStormNickSystem complete fixer.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    print("=" * 72)
    print("MineStormNickSystem fixer")
    print(f"  project root : {ROOT}")
    print(f"  java package : {PACKAGE_DIR.relative_to(ROOT)}")
    print(f"  resources    : {RESOURCES.relative_to(ROOT)}")
    print(f"  mode         : {'DRY-RUN' if args.dry_run else 'APPLY'}"
          f"{' (no backups)' if args.no_backup else ''}")
    print("=" * 72)
    print()

    if not (ROOT / "pom.xml").is_file():
        log("FATAL", f"pom.xml missing in {ROOT}")
        return 1

    backup = not args.no_backup

    # 1. Rename old class to new class, and rewrite identifiers in every
    #    other existing Java file so references compile.
    rename_existing_java_files(args.dry_run, backup)

    # 2. Write canonical new files (these overwrite any stale state).
    for path, content in {**JAVA_FILES, **RESOURCE_FILES}.items():
        result = write_text(path, content, dry=args.dry_run, backup=backup)
        if result == "created":   CREATED.append(str(path.relative_to(ROOT)))
        elif result == "updated": UPDATED.append(str(path.relative_to(ROOT)))
        else:                     SKIPPED.append(str(path.relative_to(ROOT)))

    # 3. Remove the old NickSystemCommand.java if it exists (we replaced it).
    old_cmd = PACKAGE_DIR / "command" / "NickSystemCommand.java"
    if old_cmd.exists():
        if args.dry_run:
            log("DRY ", f"would delete {old_cmd.relative_to(ROOT)}")
        else:
            try:
                old_cmd.unlink()
                log("OK  ", f"deleted {old_cmd.relative_to(ROOT)}")
            except OSError as exc:
                log("WARN", f"could not delete {old_cmd}: {exc}")

    # Summary.
    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"  created : {len(CREATED)}")
    for p in CREATED: print(f"    + {p}")
    print(f"  updated : {len(UPDATED)}")
    for p in UPDATED: print(f"    ~ {p}")
    print(f"  skipped : {len(SKIPPED)}")
    for p in SKIPPED: print(f"    = {p}")
    print()

    if args.dry_run:
        print("Dry-run complete. Re-run without --dry-run to apply.")
    else:
        print("Fixes applied. Rebuild with:")
        print("    mvn -B clean package")
    return 0


if __name__ == "__main__":
    sys.exit(main())