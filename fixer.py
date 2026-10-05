#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NickSystem - complete fixer.

Writes the final, correct version of every affected file. Safe to run
repeatedly: each file is only rewritten if its content differs from the
expected result (idempotent). A .bak copy of any file that changes is
created on the first run.

Run from the plugin project root (the folder containing pom.xml):

    python3 fixer.py                # apply all fixes
    python3 fixer.py --dry-run      # preview only
    python3 fixer.py --no-backup    # skip .bak files
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap: locate project root, source dirs, package dir.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def find_project_root() -> Path:
    """Walk up from the script dir until pom.xml is found."""
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "pom.xml").is_file():
            return candidate
    raise SystemExit(
        "FATAL: pom.xml not found. Run fixer.py from the plugin project root."
    )


ROOT = find_project_root()
SRC_JAVA = ROOT / "src" / "main" / "java"
RESOURCES = ROOT / "src" / "main" / "resources"


def find_package_dir() -> Path:
    """
    Locate the directory that contains NickPlugin.java.
    Preferred: src/main/java/com/yourname/nick
    Fallback: recursive search.
    """
    preferred = SRC_JAVA / "com" / "yourname" / "nick"
    if (preferred / "NickPlugin.java").is_file():
        return preferred
    for path in SRC_JAVA.rglob("NickPlugin.java"):
        return path.parent
    # Nothing to upgrade -- we will create the preferred location.
    return preferred


PACKAGE_DIR = find_package_dir()

# ─────────────────────────────────────────────────────────────────────────────
# Logging & IO helpers.
# ─────────────────────────────────────────────────────────────────────────────

LOG: list[tuple[str, str]] = []
CREATED: list[str] = []
UPDATED: list[str] = []
SKIPPED: list[str] = []


def log(level: str, message: str) -> None:
    line = f"[{level:<4}] {message}"
    LOG.append((level, message))
    print(line)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path, content: str, *, dry: bool, backup: bool) -> str:
    """
    Write content to path if it differs from what is already there.

    Returns one of: 'created', 'updated', 'skipped'.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            existing = None
        if existing is not None and sha(existing) == sha(content):
            log("SKIP", f"{path.relative_to(ROOT)} (already up to date)")
            return "skipped"
        if dry:
            log("DRY ", f"would update {path.relative_to(ROOT)}")
            return "updated"
        if backup:
            bak = path.with_suffix(path.suffix + ".bak")
            try:
                shutil.copy2(path, bak)
            except OSError as exc:
                log("WARN", f"could not create backup for {path}: {exc}")
        path.write_text(content, encoding="utf-8", newline="\n")
        log("OK  ", f"updated {path.relative_to(ROOT)}")
        return "updated"

    if dry:
        log("DRY ", f"would create {path.relative_to(ROOT)}")
        return "created"
    path.write_text(content, encoding="utf-8", newline="\n")
    log("OK  ", f"created {path.relative_to(ROOT)}")
    return "created"


# ─────────────────────────────────────────────────────────────────────────────
# File contents. All strings are raw so Java source keeps its backslashes.
# ─────────────────────────────────────────────────────────────────────────────

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/task/ActionBarTask.java
# ---------------------------------------------------------------------------
JAVA_ACTIONBAR = r'''package com.yourname.nick.task;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import net.md_5.bungee.api.ChatMessageType;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

/**
 * Sends the "you are nicked" indicator through the action bar, never
 * through chat. Only players with an active (or, when configured, a
 * dormant) disguise receive the message.
 *
 * <p>Bug fixed: the previous implementation called
 * {@link Player#sendMessage(String)} every scheduler tick which spammed
 * the public chat with "You are currently NICKED" and got compounded on
 * every plugin reload (which is where the "(3)" suffix came from).</p>
 */
public final class ActionBarTask implements Runnable {

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;
    private final String indicator;
    private final boolean showWhenDormant;

    public ActionBarTask(NickPlugin plugin,
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
        if (this.indicator.isEmpty()) {
            return;
        }
        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player == null || !player.isOnline()) {
                continue;
            }
            if (!profile.active() && !this.showWhenDormant) {
                continue;
            }
            try {
                player.spigot().sendMessage(
                        ChatMessageType.ACTION_BAR,
                        TextComponent.fromLegacyText(this.indicator));
            } catch (Throwable ignored) {
                // One bad player connection must never kill the task.
            }
        }
    }
}
'''

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/packet/PacketManager.java
# ---------------------------------------------------------------------------
JAVA_PACKET_MANAGER = r'''package com.yourname.nick.packet;

import com.mojang.authlib.GameProfile;
import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;

/**
 * Sends real 1.8.8 packets so nick changes appear in the tab list
 * immediately, without a relog.
 *
 * <p>Fixed: refreshTabList used to mutate the GameProfile field, send
 * REMOVE_PLAYER + ADD_PLAYER and then *restore* the original profile,
 * so the tab list reverted to the real name on the next vanilla packet.
 * The new implementation updates EntityPlayer.listName with a
 * ChatComponentText and broadcasts UPDATE_DISPLAY_NAME, then keeps the
 * GameProfile.name in sync.</p>
 */
public final class PacketManager {

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;

    private Class<?> packetInfoClass;
    private Class<?> packetDestroyClass;
    private Class<?> packetSpawnClass;
    private Class<?> packetClass;
    private Class<?> enumPlayerInfoActionClass;
    private Class<?> entityPlayerClass;
    private Class<?> entityHumanClass;
    private Class<?> worldServerClass;
    private Class<?> playerConnectionClass;

    private Method getHandleMethod;
    private Field  playerConnectionField;
    private Method sendPacketMethod;
    private Method getProfileMethod;
    private Method getIdMethod;
    private Method setLocationMethod;   // optional
    private Method spawnInMethod;       // optional

    private boolean enabled = false;

    public PacketManager(NickPlugin plugin, DisguiseRegistry registry) {
        this.plugin = plugin;
        this.registry = registry;
    }

    /* ------------------------------------------------------------------ */
    /*  Lifecycle                                                         */
    /* ------------------------------------------------------------------ */

    public void load() {
        // nothing to do
    }

    public boolean enable() {
        try {
            String pkg = "net.minecraft.server.v1_8_R3.";
            this.packetInfoClass    = Class.forName(pkg + "PacketPlayOutPlayerInfo");
            this.packetDestroyClass = Class.forName(pkg + "PacketPlayOutEntityDestroy");
            this.packetSpawnClass   = Class.forName(pkg + "PacketPlayOutNamedEntitySpawn");
            this.packetClass        = Class.forName(pkg + "Packet");
            this.enumPlayerInfoActionClass =
                    Class.forName(pkg + "PacketPlayOutPlayerInfo$EnumPlayerInfoAction");
            this.entityPlayerClass  = Class.forName(pkg + "EntityPlayer");
            this.entityHumanClass   = Class.forName(pkg + "EntityHuman");
            this.worldServerClass   = Class.forName(pkg + "WorldServer");
            this.playerConnectionClass = Class.forName(pkg + "PlayerConnection");

            Class<?> craftPlayer = Class.forName(
                    "org.bukkit.craftbukkit.v1_8_R3.entity.CraftPlayer");
            this.getHandleMethod = craftPlayer.getMethod("getHandle");
            this.playerConnectionField = this.entityPlayerClass.getField("playerConnection");
            this.sendPacketMethod = this.playerConnectionClass.getMethod(
                    "sendPacket", this.packetClass);
            this.getProfileMethod = this.entityHumanClass.getMethod("getProfile");
            this.getIdMethod = this.entityPlayerClass.getMethod("getId");

            this.setLocationMethod = tryGetMethod(this.entityPlayerClass,
                    "setLocation", double.class, double.class, double.class,
                    float.class, float.class);
            this.spawnInMethod = tryGetMethod(this.entityPlayerClass,
                    "spawnIn", this.worldServerClass);
            if (this.spawnInMethod == null) {
                this.spawnInMethod = tryGetMethod(this.entityPlayerClass, "spawnIn");
            }

            this.enabled = true;
            this.plugin.getLogger().info(
                    "PacketManager: hooks installed"
                    + (this.spawnInMethod == null
                            ? " (nametag respawn disabled on this server fork)"
                            : ""));
            return true;
        } catch (Throwable t) {
            this.plugin.getLogger().warning(
                    "PacketManager: could not install NMS hooks - " + t);
            this.enabled = false;
            return false;
        }
    }

    public void disable() {
        this.enabled = false;
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                        */
    /* ------------------------------------------------------------------ */

    public void refreshTabList(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) {
            return;
        }
        try {
            Object handle = this.getHandleMethod.invoke(target);
            String nick = resolveNick(target);
            if (nick == null || nick.isEmpty()) {
                return;
            }

            // 1.8.8 tab-list display name lives on EntityPlayer.listName.
            Field listName = findField(handle.getClass(), "listName");
            if (listName != null) {
                listName.setAccessible(true);
                Class<?> cc = Class.forName(
                        "net.minecraft.server.v1_8_R3.ChatComponentText");
                listName.set(handle, cc.getConstructor(String.class)
                        .newInstance(nick));
            }

            // Keep the GameProfile in sync (permanently - no restore).
            Object profile = this.getProfileMethod.invoke(handle);
            if (profile != null) {
                try {
                    Method setName =
                            profile.getClass().getMethod("setName", String.class);
                    setName.setAccessible(true);
                    setName.invoke(profile, nick);
                } catch (Throwable ignored) {
                    // authlib variant without setName - ignore.
                }
            }

            List<Object> players = new ArrayList<Object>();
            players.add(handle);
            Object updateAction = enumAction("UPDATE_DISPLAY_NAME");
            Object packet = buildInfoPacket(updateAction, players);
            broadcast(packet);
        } catch (Throwable t) {
            this.plugin.getLogger().warning("refreshTabList failed: " + t);
        }
    }

    public void refreshNametag(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) {
            return;
        }
        if (this.spawnInMethod == null) {
            refreshTabList(target);
            return;
        }
        try {
            Object handle = this.getHandleMethod.invoke(target);
            int entityId = (Integer) this.getIdMethod.invoke(handle);

            Object destroyPacket = this.packetDestroyClass
                    .getConstructor(int[].class)
                    .newInstance((Object) new int[] { entityId });

            Object world = target.getWorld();
            Object worldServer = world.getClass()
                    .getMethod("getHandle").invoke(world);

            if (this.setLocationMethod != null) {
                this.setLocationMethod.invoke(handle,
                        target.getLocation().getX(),
                        target.getLocation().getY(),
                        target.getLocation().getZ(),
                        target.getLocation().getYaw(),
                        target.getLocation().getPitch());
            }

            if (this.spawnInMethod.getParameterTypes().length == 1) {
                this.spawnInMethod.invoke(handle, worldServer);
            } else {
                this.spawnInMethod.invoke(handle);
            }

            Object spawnPacket = this.packetSpawnClass
                    .getConstructor(this.entityHumanClass)
                    .newInstance(handle);

            for (Player viewer : Bukkit.getOnlinePlayers()) {
                if (viewer.equals(target)) {
                    continue;
                }
                sendPacket(viewer, destroyPacket);
                sendPacket(viewer, spawnPacket);
            }

            refreshTabList(target);
        } catch (Throwable t) {
            this.plugin.getLogger().warning("refreshNametag failed: " + t);
        }
    }

    public void resendOwnEntry(Player player) {
        if (player == null || !player.isOnline()) {
            return;
        }
        refreshTabList(player);
        refreshNametag(player);
    }

    /* ------------------------------------------------------------------ */
    /*  Internal helpers                                                  */
    /* ------------------------------------------------------------------ */

    private static Method tryGetMethod(Class<?> clazz, String name, Class<?>... params) {
        try {
            Method m = clazz.getMethod(name, params);
            m.setAccessible(true);
            return m;
        } catch (NoSuchMethodException e) {
            return null;
        }
    }

    private static Field findField(Class<?> clazz, String name) {
        Class<?> c = clazz;
        while (c != null) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f;
            } catch (NoSuchFieldException ignored) {
                c = c.getSuperclass();
            }
        }
        return null;
    }

    private String resolveNick(Player player) {
        DisguiseProfile profile =
                this.registry.get(player.getUniqueId()).orElse(null);
        return profile == null ? null : profile.nickname();
    }

    private Field findProfileField(Class<?> clazz) {
        return findField(clazz, "profile");
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private Object enumAction(String name) throws Exception {
        return Enum.valueOf(
                (Class<? extends Enum>) this.enumPlayerInfoActionClass, name);
    }

    private Object buildInfoPacket(Object action, List<Object> players)
            throws Exception {
        for (java.lang.reflect.Constructor<?> ctor
                : this.packetInfoClass.getConstructors()) {
            Class<?>[] params = ctor.getParameterTypes();
            if (params.length == 2
                    && params[0] == this.enumPlayerInfoActionClass
                    && Iterable.class.isAssignableFrom(params[1])) {
                return ctor.newInstance(action, players);
            }
        }
        if (!players.isEmpty()) {
            for (java.lang.reflect.Constructor<?> ctor
                    : this.packetInfoClass.getConstructors()) {
                Class<?>[] params = ctor.getParameterTypes();
                if (params.length == 2
                        && params[0] == this.enumPlayerInfoActionClass
                        && params[1] == this.entityPlayerClass) {
                    return ctor.newInstance(action, players.get(0));
                }
            }
        }
        throw new IllegalStateException("No usable PacketPlayOutPlayerInfo ctor");
    }

    private void broadcast(Object packet) throws Exception {
        for (Player online : Bukkit.getOnlinePlayers()) {
            sendPacket(online, packet);
        }
    }

    private void sendPacket(Player player, Object packet) throws Exception {
        Object handle = this.getHandleMethod.invoke(player);
        Object connection = this.playerConnectionField.get(handle);
        this.sendPacketMethod.invoke(connection, packet);
    }
}
'''

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/gui/GuiConfig.java  (NEW)
# ---------------------------------------------------------------------------
JAVA_GUI_CONFIG = r'''package com.yourname.nick.gui;

import java.io.File;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Typed, defaulted reader for gui.yml. Every string that appears inside
 * the /nick setup book is resolved through this class so server owners
 * can restyle the book without recompiling.
 */
public final class GuiConfig {

    public static final class Button {
        private final String label;
        private final String command;
        private final String hover;

        public Button(String label, String command, String hover) {
            this.label = color(label);
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
            try {
                plugin.saveResource("gui.yml", false);
            } catch (Throwable ignored) {
            }
        }
        this.yaml = YamlConfiguration.loadConfiguration(f);
    }

    public String title() {
        return color(this.yaml.getString("book.title", "Nickname Setup"));
    }

    public String author() {
        return color(this.yaml.getString("book.author", "NickSystem"));
    }

    public String get(String path) {
        return this.yaml.getString(path, "");
    }

    public List<String> list(String path) {
        List<String> l = this.yaml.getStringList(path);
        return l == null ? Collections.<String>emptyList() : l;
    }

    /** Reads {@code <path>-color}, e.g. intro-color: DARK_AQUA. */
    public ChatColor color(String path) {
        String raw = this.yaml.getString(path + "-color", "BLACK");
        try {
            return ChatColor.valueOf(raw.toUpperCase());
        } catch (Throwable t) {
            return ChatColor.BLACK;
        }
    }

    /** Reads {@code <path>-style}, e.g. intro-style: BOLD. Returns null if blank. */
    public ChatColor style(String path) {
        String raw = this.yaml.getString(path + "-style", "");
        if (raw == null || raw.isEmpty()) {
            return null;
        }
        try {
            return ChatColor.valueOf(raw.toUpperCase());
        } catch (Throwable t) {
            return null;
        }
    }

    public Button button(String key) {
        String base = "buttons." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                this.yaml.getString(base + "command", ""),
                this.yaml.getString(base + "hover", ""));
    }

    public static String color(String s) {
        return ChatColor.translateAlternateColorCodes('&', s == null ? "" : s);
    }
}
'''

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/gui/BookGUIManager.java
# ---------------------------------------------------------------------------
JAVA_BOOK_GUI = r'''package com.yourname.nick.gui;

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
import org.bukkit.inventory.ItemStack;

/**
 * Book-driven nickname setup. Every step is rendered inside a written
 * book with clickable / hoverable text so the chat is never used for
 * UI navigation.
 *
 * <p>All strings come from gui.yml through {@link GuiConfig}.</p>
 */
public final class BookGUIManager {

    private final NickPlugin plugin;
    private final Messages messages;
    private final GuiConfig gui;
    private final DisguiseManager disguises;
    private final SkinCacheManager skins;
    private final NameGenerator generator;
    private final NameValidator validator;
    private final StorageManager storage;

    private final Map<UUID, NickSession> sessions =
            new ConcurrentHashMap<UUID, NickSession>();

    public BookGUIManager(NickPlugin plugin,
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
            @Override
            public void accept(final Optional<NickRecord> last, final Throwable error) {
                Async.main(BookGUIManager.this.plugin, new Runnable() {
                    @Override
                    public void run() {
                        if (!player.isOnline()) {
                            return;
                        }
                        NickRecord history =
                                (error == null && last != null && last.isPresent())
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
        if (session == null) {
            open(player);
            return;
        }
        if (args.length == 0) {
            showIntro(player);
            return;
        }
        String sub = args[0].toLowerCase(Locale.ROOT);
        if ("rank".equals(sub)) {
            chooseRank(player, session, args);
        } else if ("skin".equals(sub)) {
            chooseSkin(player, session, args);
        } else if ("name".equals(sub)) {
            chooseName(player, session, args);
        } else if ("use".equals(sub)) {
            useRolledName(player, session);
        } else if ("reroll".equals(sub)) {
            rollName(player, session);
        } else if ("close".equals(sub)) {
            // book already closed
        } else {
            showIntro(player);
        }
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
        out.add(line(gui.color("intro.title"), gui.style("intro.title"),
                gui.get("intro.title")));
        out.add(blank());
        for (String l : gui.list("intro.lines")) {
            out.add(line(ChatColor.BLACK, null, l));
        }
        out.add(blank());
        GuiConfig.Button b = gui.button("start");
        out.add(button(b.label(), b.command(), b.hover()));
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showRankPicker(Player player) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(gui.color("rank.title"), gui.style("rank.title"),
                gui.get("rank.title")));
        out.add(blank());
        for (String l : gui.list("rank.lines")) {
            out.add(line(ChatColor.BLACK, null, l));
        }
        out.add(blank());
        for (Rank r : Rank.values()) {
            out.add(button("[" + r.label() + "]",
                    "/nick ui rank " + r.name(),
                    "Use " + r.label()));
        }
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showSkin(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(gui.color("skin.title"), gui.style("skin.title"),
                gui.get("skin.title")));
        out.add(blank());
        for (String l : gui.list("skin.lines")) {
            out.add(line(ChatColor.BLACK, null, l));
        }
        out.add(blank());
        addButton(out, "skin.normal",  "/nick ui skin normal",  "Keep your own skin");
        addButton(out, "skin.default", "/nick ui skin default", "Default skin");
        addButton(out, "skin.random",  "/nick ui skin random",  "Random from pool");
        if (session.history() != null) {
            addButton(out, "skin.reuse", "/nick ui skin reuse",
                    "Your last nickname's skin");
        }
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showName(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(gui.color("name.title"), gui.style("name.title"),
                gui.get("name.title")));
        out.add(blank());
        for (String l : gui.list("name.lines")) {
            out.add(line(ChatColor.BLACK, null, l));
        }
        out.add(blank());
        addButton(out, "name.random", "/nick ui name random",
                "Generate a random username");
        if (session.history() != null) {
            addButton(out, "name.reuse", "/nick ui name reuse",
                    "Your last nickname");
        }
        out.add(blank());
        addButton(out, "name.reset", "/nick reset",
                "Go back to your real name");
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showRolledName(Player player, NickSession session) {
        String name = session.pendingName();
        if (name == null) {
            showName(player, session);
            return;
        }
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(gui.color("rolled.title"), gui.style("rolled.title"),
                gui.get("rolled.title")));
        out.add(blank());
        for (String l : gui.list("rolled.lines")) {
            out.add(line(ChatColor.BLACK, null, l));
        }
        out.add(blank());
        out.add(line(ChatColor.YELLOW, ChatColor.BOLD, name));
        out.add(blank());
        addButton(out, "rolled.use",   "/nick ui use",    "Nick as " + name);
        addButton(out, "rolled.again", "/nick ui reroll", "Generate a different name");
        openBook(player, out.toArray(new BaseComponent[out.size()]));
    }

    private void showFinished(Player player, String nick) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line(gui.color("done.title"), gui.style("done.title"),
                gui.get("done.title")));
        out.add(blank());
        for (String l : gui.list("done.lines")) {
            out.add(line(ChatColor.BLACK, null, l));
        }
        out.add(line(ChatColor.YELLOW, ChatColor.BOLD, nick));
        out.add(blank());
        for (String l : gui.list("done.footer")) {
            out.add(line(ChatColor.DARK_GRAY, null, l));
        }
        openBook(player, out.toArray(new BaseComponent[out.size()]));
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

    private void addButton(List<BaseComponent> out, String key,
                           String fallbackCmd, String fallbackHover) {
        GuiConfig.Button b = gui.button(key);
        String cmd = (b.command() == null || b.command().isEmpty())
                ? fallbackCmd : b.command();
        String hover = (b.hover() == null || b.hover().isEmpty())
                ? fallbackHover : b.hover();
        String label = (b.label() == null || b.label().isEmpty())
                ? ("[ " + key + " ]") : b.label();
        out.add(button(label, cmd, hover));
    }

    private void openBook(Player player, BaseComponent[] page) {
        ItemStack book = VirtualBook.buildComponents(gui.title(), gui.author(), page);
        VirtualBook.open(player, book, page);
    }

    private static BaseComponent blank() {
        return new TextComponent(TextComponent.fromLegacyText("\n"));
    }

    private static BaseComponent line(ChatColor colour, ChatColor style, String text) {
        StringBuilder sb = new StringBuilder();
        sb.append(colour == null ? "" : colour.toString());
        if (style != null) {
            sb.append(style.toString());
        }
        sb.append(text == null ? "" : text).append('\n');
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

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/integration/LuckPermsHook.java  (NEW)
# ---------------------------------------------------------------------------
JAVA_LUCKPERMS_HOOK = r'''package com.yourname.nick.integration;

import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * LuckPerms integration via reflection - no hard dependency.
 *
 * <p>When LuckPerms is present, the player's primary group is compared
 * against {@code luckperms.required-group} and (if enabled) against every
 * group that inherits from it. When LuckPerms is missing or errors, the
 * hook falls back to a plain permission-node check so /g still works on
 * networks that only use permission plugins.</p>
 */
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
        this.checkInheritance =
                cfg.getBoolean("luckperms.check-inheritance", true);
        this.fallbackPermission = cfg.getString(
                "luckperms.required-permission", "nicksystem.global");
        this.trackedGroups.clear();
        for (String g : cfg.getStringList("luckperms.tracked-groups")) {
            if (g != null && !g.trim().isEmpty()) {
                this.trackedGroups.add(g.toLowerCase(Locale.ROOT));
            }
        }
        if (this.trackedGroups.isEmpty()) {
            this.trackedGroups.add(this.requiredGroup);
        }
    }

    /** True if the player satisfies the required rank. */
    public boolean isRanked(Player player) {
        if (player == null) {
            return false;
        }
        if (this.enabled && hasLuckPerms()) {
            try {
                if (checkViaLuckPerms(player)) {
                    return true;
                }
            } catch (Throwable t) {
                this.plugin.getLogger().fine(
                        "LuckPerms lookup failed, falling back: " + t);
            }
        }
        for (String g : this.trackedGroups) {
            if (player.hasPermission("group." + g)) {
                return true;
            }
        }
        return player.hasPermission(this.fallbackPermission);
    }

    private boolean hasLuckPerms() {
        try {
            Class.forName("net.luckperms.api.LuckPermsProvider");
            return this.plugin.getServer()
                    .getPluginManager().isPluginEnabled("LuckPerms");
        } catch (Throwable t) {
            return false;
        }
    }

    private boolean checkViaLuckPerms(Player player) throws Exception {
        Class<?> provider = Class.forName("net.luckperms.api.LuckPermsProvider");
        Object luckPerms  = provider.getMethod("get").invoke(null);
        Object userMgr    = luckPerms.getClass().getMethod("getUserManager")
                .invoke(luckPerms);
        Object user = userMgr.getClass()
                .getMethod("getUser", UUID.class)
                .invoke(userMgr, player.getUniqueId());
        if (user == null) {
            return false;
        }
        Object cached = user.getClass().getMethod("getCachedData").invoke(user);
        Object meta   = cached.getClass().getMethod("getMetaData").invoke(cached);
        String primaryGroup = String.valueOf(
                meta.getClass().getMethod("getPrimaryGroup").invoke(meta))
                .toLowerCase(Locale.ROOT);

        if (this.trackedGroups.contains(primaryGroup)) {
            return true;
        }
        if (!this.checkInheritance) {
            return false;
        }
        try {
            Method getInherited =
                    meta.getClass().getMethod("getInheritedGroups");
            Object inherited = getInherited.invoke(meta);
            if (inherited instanceof Iterable) {
                for (Object g : (Iterable<?>) inherited) {
                    String n = String.valueOf(g).toLowerCase(Locale.ROOT);
                    if (this.trackedGroups.contains(n)) {
                        return true;
                    }
                }
            }
        } catch (NoSuchMethodException ignored) {
            for (String tracked : this.trackedGroups) {
                if (primaryGroup.contains(tracked)) {
                    return true;
                }
            }
        }
        return false;
    }

    public String requiredGroup() {
        return this.requiredGroup;
    }
}
'''

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/command/GlobalCommand.java  (NEW)
# ---------------------------------------------------------------------------
JAVA_GLOBAL_COMMAND = r'''package com.yourname.nick.command;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.integration.LuckPermsHook;
import com.yourname.nick.message.Messages;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;

/**
 * /g &lt;message&gt; - broadcasts a global message, but only for players in
 * the configured LuckPerms group (default: "prime") or above.
 */
public final class GlobalCommand implements TabExecutor {

    private final NickPlugin plugin;
    private final Messages messages;
    private final LuckPermsHook luckPerms;

    public GlobalCommand(NickPlugin plugin, Messages messages, LuckPermsHook luckPerms) {
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

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/command/NickSystemCommand.java  (NEW)
# ---------------------------------------------------------------------------
JAVA_NICKSYSTEM_COMMAND = r'''package com.yourname.nick.command;

import com.yourname.nick.NickPlugin;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;

/**
 * /nicksystem reload - reloads config.yml, gui.yml, messages.yml and
 * names.yml, cancels old tasks and reschedules them (idempotent).
 */
public final class NickSystemCommand implements TabExecutor {

    private final NickPlugin plugin;

    public NickSystemCommand(NickPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command,
                             String label, String[] args) {
        if (!sender.hasPermission("nicksystem.admin")) {
            sender.sendMessage(ChatColor.RED + "No permission.");
            return true;
        }
        if (args.length == 0 || !"reload".equalsIgnoreCase(args[0])) {
            sender.sendMessage(ChatColor.GOLD + "/nicksystem reload");
            return true;
        }
        this.plugin.reloadEverything();
        sender.sendMessage(ChatColor.GREEN + "NickSystem reloaded.");
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender s, Command c,
                                      String a, String[] args) {
        if (args.length == 1) {
            String typed = args[0].toLowerCase(Locale.ROOT);
            if ("reload".startsWith(typed)) {
                return Arrays.asList("reload");
            }
        }
        return Collections.emptyList();
    }
}
'''

# ---------------------------------------------------------------------------
# Java: com/yourname/nick/NickPlugin.java
# ---------------------------------------------------------------------------
JAVA_NICK_PLUGIN = r'''package com.yourname.nick;

import com.yourname.nick.command.GlobalCommand;
import com.yourname.nick.command.NickCommand;
import com.yourname.nick.command.NickSystemCommand;
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

public final class NickPlugin extends JavaPlugin {

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

    /** Tracked so /reload and /nicksystem reload cannot stack duplicates. */
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
        bind("nicksystem", new NickSystemCommand(this));
        bind("g",          new GlobalCommand(this, this.messages, this.luckPerms));

        scheduleTasks();

        if (pm.isPluginEnabled("PlaceholderAPI")) {
            final NickPlaceholderExpansion expansion =
                    new NickPlaceholderExpansion(this, this.registry, this.bedwars);
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

    /** Called by /nicksystem reload. Never throws. */
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

            getLogger().info("NickSystem reloaded.");
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
                    @Override
                    public void run() {
                        registry.prunePending(60000L);
                    }
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
        if (!file.exists()) {
            saveResource("names.yml", false);
        }
        return YamlConfiguration.loadConfiguration(file);
    }

    private void saveResourceIfMissing(String name) {
        File f = new File(getDataFolder(), name);
        if (!f.exists()) {
            try {
                saveResource(name, false);
            } catch (IllegalArgumentException ignored) {
                // Resource not bundled - ignore.
            }
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

# ---------------------------------------------------------------------------
# Resource: plugin.yml
# ---------------------------------------------------------------------------
RES_PLUGIN_YML = r'''name: NickSystem
version: '1.0.0'
main: com.yourname.nick.NickPlugin
api-version: '1.8'
description: Nickname system for Spigot/Paper 1.8.8 (built for JDK 8+).
authors: [YourName]
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
  nicksystem:
    description: Manage the NickSystem plugin.
    usage: /nicksystem reload
    aliases: [ns]
    permission: nicksystem.admin
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
  nicksystem.admin:
    description: Use /nicksystem reload.
    default: op
  nicksystem.global:
    description: Fallback permission for /g when LuckPerms is not installed.
    default: op
'''

# ---------------------------------------------------------------------------
# Resource: config.yml
# ---------------------------------------------------------------------------
RES_CONFIG_YML = r'''# NickSystem configuration
#
# Database credentials can be supplied through environment variables so they
# never have to be written to disk or committed. An environment variable that is
# set and non-blank always wins over the value in this file:
#   NICK_DB_TYPE      sqlite | mysql
#   NICK_DB_HOST      MySQL host
#   NICK_DB_PORT      MySQL port
#   NICK_DB_NAME      MySQL database name
#   NICK_DB_USER      MySQL username
#   NICK_DB_PASSWORD  MySQL password
#   NICK_DB_SSL       true | false

settings:
  # Restore a player's nickname automatically when they log in again.
  persist-across-sessions: true
  # Render nicked players with their fake rank and name in chat.
  rewrite-chat: true
  # Mask the real name in join and quit messages while the disguise is active.
  rewrite-join-quit: true

# Worlds in which the disguise is active. Everywhere else the nick stays dormant.
# mode WHITELIST: only listed worlds are active.
# mode BLACKLIST: every world except the listed ones is active.
# '*' is a wildcard and matching is case-insensitive.
# World restrictions are no longer used - nicks are
# applied instantly and everywhere.
#worlds:
#  mode: WHITELIST
#  list:
#    - "bedwars_*"
#    - "arena_*"
#    - "skywars_*"
#
actionbar:
  enabled: true
  interval-ticks: 40
  # Also show the indicator while the nick is dormant (for example in a lobby).
  show-when-dormant: true

storage:
  type: sqlite
  sqlite-file: nick.db
  mysql:
    host: localhost
    port: 3306
    database: nicksystem
    # Leave username and password empty and use the environment variables.
    username: ""
    password: ""
    use-ssl: false

skins:
  cache-ttl-minutes: 1440
  request-timeout-seconds: 10
  # Mojang usernames whose skins form the random pool. Resolved asynchronously
  # at startup and cached on disk.
  pool-players: []
  # Raw texture pairs for the random pool (value and signature from the Mojang
  # session server). Example:
  # pool:
  #   - label: "Example"
  #     value: "eyJ0aW1lc3RhbXAiOi..."
  #     signature: "Zm9vYmFy..."
  pool: []

integrations:
  bedwars:
    # Spoof a low star count while a player is nicked and the disguise is active.
    enabled: false
    min-stars: 1
    max-stars: 12
    # Prefix the star count to the nicked chat format.
    chat-prefix: true
    # Placeholder that returns the real level of the Bedwars plugin you use.
    # Resolved through PlaceholderAPI when the player is not disguised.
    # Never use a %nick_...% placeholder here.
    real-level-placeholder: ""

# ---------------------------------------------------------------------------
# LuckPerms integration - controls who can use /g.
# ---------------------------------------------------------------------------
luckperms:
  # Master switch. When false, /g falls back to permission nodes only.
  enabled: true
  # Any player whose primary LuckPerms group is this one - or inherits from
  # it when check-inheritance is true - may use /g.
  required-group: "prime"
  # Include groups that inherit from required-group (e.g. elite, mvp, ...).
  check-inheritance: true
  # Explicit list of *additional* accepted groups. Leave empty to auto-use
  # required-group only.
  tracked-groups:
    - prime
    - elite
    - mvp
  # Fallback permission node used when LuckPerms is missing or errors.
  required-permission: "nicksystem.global"
'''

# ---------------------------------------------------------------------------
# Resource: gui.yml  (NEW)
# ---------------------------------------------------------------------------
RES_GUI_YML = r'''# -----------------------------------------------------------------------------
# gui.yml - every string shown inside the /nick setup book.
# Colour codes: legacy '&' codes. Title/author are the book's own fields.
# This file is hot-reloadable with /nicksystem reload.
# -----------------------------------------------------------------------------

book:
  title:  "Nickname Setup"
  author: "NickSystem"

# -- Intro page --------------------------------------------------------------
intro:
  title: "Nickname Setup"
  title-color: "DARK_AQUA"
  title-style: "BOLD"
  lines:
    - "Nicknames let you play"
    - "with a different name."
    - ""
    - "All server rules still"
    - "apply and every nick"
    - "is logged."

# -- Rank picker -------------------------------------------------------------
rank:
  title: "Choose your RANK"
  title-color: "DARK_AQUA"
  title-style: "BOLD"
  lines:
    - "Pick the rank you"
    - "will show while nicked."

# -- Skin picker -------------------------------------------------------------
skin:
  title: "Choose your SKIN"
  title-color: "DARK_AQUA"
  title-style: "BOLD"
  lines:
    - "Pick the skin you"
    - "will wear while nicked."

# -- Name picker -------------------------------------------------------------
name:
  title: "Choose your NAME"
  title-color: "DARK_AQUA"
  title-style: "BOLD"
  lines:
    - "How do you want"
    - "to be called?"

# -- Rolled-name preview -----------------------------------------------------
rolled:
  title: "Random name"
  title-color: "DARK_AQUA"
  title-style: "BOLD"
  lines:
    - "We generated:"

# -- Finished ----------------------------------------------------------------
done:
  title: "Nickname ready!"
  title-color: "DARK_AQUA"
  title-style: "BOLD"
  lines:
    - "You are now nicked as:"
  footer:
    - "The disguise is active"
    - "everywhere right away."
    - ""
    - "Close the book when done."

# -- Buttons (label / command / hover) ---------------------------------------
buttons:
  start:
    label:   "[ Start setup ]"
    command: "/nick ui rank"
    hover:   "Begin the setup"
  skin:
    normal:
      label:   "[ My normal skin ]"
      command: "/nick ui skin normal"
      hover:   "Keep your own skin"
    default:
      label:   "[ Steve/Alex ]"
      command: "/nick ui skin default"
      hover:   "Default skin"
    random:
      label:   "[ Random skin ]"
      command: "/nick ui skin random"
      hover:   "Random from pool"
    reuse:
      label:   "[ Reuse last skin ]"
      command: "/nick ui skin reuse"
      hover:   "Your last nickname's skin"
  name:
    random:
      label:   "[ Random name ]"
      command: "/nick ui name random"
      hover:   "Generate a random username"
    reuse:
      label:   "[ Reuse last name ]"
      command: "/nick ui name reuse"
      hover:   "Your last nickname"
    reset:
      label:   "[ Reset nickname ]"
      command: "/nick reset"
      hover:   "Go back to your real name"
  rolled:
    use:
      label:   "[ USE THIS NAME ]"
      command: "/nick ui use"
      hover:   "Confirm this nickname"
    again:
      label:   "[ TRY AGAIN ]"
      command: "/nick ui reroll"
      hover:   "Generate a different name"
'''

# ---------------------------------------------------------------------------
# Resource: messages.yml  (actionbar normalised, counters stripped)
# ---------------------------------------------------------------------------
RES_MESSAGES_YML = r'''# NickSystem messages (legacy colour codes, Minecraft 1.8.8 compatible)

prefix: "&8[&6Nick&8] &r"

player-only: "&cThis command can only be used by players."
usage: "&cUsage: /nick, /nick reset, /nick skin [player], /nick name [name]"
no-permission: "&cYou do not have permission to do that."
session-expired: "&cThat nickname setup has expired. Type &e/nick &cto start again."
storage-error: "&cThe nickname database is unavailable right now. Please try again shortly."

nick-finished: "&aYou have finished setting up your nickname! When you go into a game, you will be nicked as &e%nick%&a."
nick-reset: "&aYou are back to being your usual self."
nick-not-nicked: "&cYou do not currently have a nickname."

# Displayed in the ACTION BAR only - never in chat.
actionbar: "&c&lYou are currently NICKED"

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

# ---------------------------------------------------------------------------
# Mapping: relative path -> content
# ---------------------------------------------------------------------------
JAVA_FILES = {
    PACKAGE_DIR / "NickPlugin.java":
        JAVA_NICK_PLUGIN,
    PACKAGE_DIR / "task" / "ActionBarTask.java":
        JAVA_ACTIONBAR,
    PACKAGE_DIR / "packet" / "PacketManager.java":
        JAVA_PACKET_MANAGER,
    PACKAGE_DIR / "gui" / "GuiConfig.java":
        JAVA_GUI_CONFIG,
    PACKAGE_DIR / "gui" / "BookGUIManager.java":
        JAVA_BOOK_GUI,
    PACKAGE_DIR / "integration" / "LuckPermsHook.java":
        JAVA_LUCKPERMS_HOOK,
    PACKAGE_DIR / "command" / "GlobalCommand.java":
        JAVA_GLOBAL_COMMAND,
    PACKAGE_DIR / "command" / "NickSystemCommand.java":
        JAVA_NICKSYSTEM_COMMAND,
}

RESOURCE_FILES = {
    RESOURCES / "plugin.yml":   RES_PLUGIN_YML,
    RESOURCES / "config.yml":   RES_CONFIG_YML,
    RESOURCES / "gui.yml":      RES_GUI_YML,
    RESOURCES / "messages.yml": RES_MESSAGES_YML,
}


# ─────────────────────────────────────────────────────────────────────────────
# Optional post-write sanity checks.
# ─────────────────────────────────────────────────────────────────────────────

SENTINELS = {
    "NickPlugin.java":          ["reloadEverything", "actionBarTask", "NickSystemCommand"],
    "ActionBarTask.java":       ["ChatMessageType.ACTION_BAR"],
    "PacketManager.java":       ["UPDATE_DISPLAY_NAME", "findField"],
    "GuiConfig.java":           ["class GuiConfig"],
    "BookGUIManager.java":      ["GuiConfig gui"],
    "LuckPermsHook.java":       ["isRanked", "requiredGroup"],
    "GlobalCommand.java":       ["class GlobalCommand"],
    "NickSystemCommand.java":   ["class NickSystemCommand"],
    "plugin.yml":               ["nicksystem:", "  g:"],
    "config.yml":               ["luckperms:", "required-group:"],
    "gui.yml":                  ["book:", "buttons:"],
    "messages.yml":             ["actionbar:"],
}


def verify(path: Path, expected: str) -> bool:
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as exc:
        log("FAIL", f"cannot read {path}: {exc}")
        return False
    name = path.name
    for sentinel in SENTINELS.get(name, []):
        if sentinel not in actual:
            log("FAIL", f"{path.relative_to(ROOT)} missing sentinel: {sentinel!r}")
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main.
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="NickSystem complete fixer - writes every affected file.")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be written without touching disk")
    parser.add_argument("--no-backup", action="store_true",
                        help="do not create .bak copies")
    args = parser.parse_args()

    print("=" * 72)
    print("NickSystem fixer")
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

    for path, content in {**JAVA_FILES, **RESOURCE_FILES}.items():
        result = write_text(path, content, dry=args.dry_run, backup=backup)
        if result == "created":
            CREATED.append(str(path.relative_to(ROOT)))
        elif result == "updated":
            UPDATED.append(str(path.relative_to(ROOT)))
        else:
            SKIPPED.append(str(path.relative_to(ROOT)))

    # Verify.
    if not args.dry_run:
        print()
        log("CHK ", "verifying written files")
        ok = True
        for path in {**JAVA_FILES, **RESOURCE_FILES}.keys():
            if not path.exists():
                log("FAIL", f"{path.relative_to(ROOT)} was not written")
                ok = False
                continue
            if not verify(path, ""):
                ok = False
        if ok:
            log("CHK ", "all files verified")

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
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())