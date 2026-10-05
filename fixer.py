#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MineStormNickSystem - complete fixer (with LuckPerms detection).

Runs from the source root (folder containing pom.xml). Writes every
affected Java source and resource file verbatim, patches pom.xml,
refreshes any installed server copy under plugins/, and reports whether
LuckPerms is present so /g works out of the box.

Idempotent. A file is only rewritten when its content differs.

Run:
    py -3.12 fixer.py
    mvn -B clean package
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


# ───────────────────────────────────────────────────────────────────────────
#  Bootstrap
# ───────────────────────────────────────────────────────────────────────────

def find_project_root() -> Path:
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "pom.xml").is_file():
            return candidate
    raise SystemExit(
        "FATAL: pom.xml not found. Put fixer.py next to pom.xml and retry.")


ROOT = find_project_root()
SRC_JAVA = ROOT / "src" / "main" / "java"
RESOURCES = ROOT / "src" / "main" / "resources"


def find_package_dir() -> Path:
    for name in ("MineStormNickPlugin.java", "NickPlugin.java"):
        p = SRC_JAVA / "com" / "yourname" / "nick"
        if (p / name).is_file():
            return p
    for name in ("MineStormNickPlugin.java", "NickPlugin.java"):
        for path in SRC_JAVA.rglob(name):
            return path.parent
    return SRC_JAVA / "com" / "yourname" / "nick"


PACKAGE_DIR = find_package_dir()


# ───────────────────────────────────────────────────────────────────────────
#  Logging / IO
# ───────────────────────────────────────────────────────────────────────────

LOG: list[tuple[str, str]] = []
CREATED: list[str] = []
UPDATED: list[str] = []
SKIPPED: list[str] = []
DELETED: list[str] = []


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
#  JAVA SOURCES
# ═══════════════════════════════════════════════════════════════════════════

JAVA_ACTIONBAR = r'''package com.yourname.nick.task;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import net.md_5.bungee.chat.ComponentSerializer;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

public final class ActionBarTask implements Runnable {

    private static final Constructor<?> CHAT_PACKET_CTOR;
    private static final Method GET_HANDLE;
    private static final Method SEND_PACKET;
    private static final Method FROM_JSON;
    private static final Field  CONNECTION_FIELD;

    static {
        Constructor<?> ctor = null;
        Method getHandle = null;
        Method sendPacket = null;
        Method fromJson = null;
        Field  connField = null;
        try {
            Class<?> chatPacket = Class.forName("net.minecraft.server.v1_8_R3.PacketPlayOutChat");
            Class<?> chatComp   = Class.forName("net.minecraft.server.v1_8_R3.IChatBaseComponent");
            Class<?> packet     = Class.forName("net.minecraft.server.v1_8_R3.Packet");
            ctor = chatPacket.getConstructor(chatComp, byte.class);

            Class<?> craftPlayer = Class.forName(
                    "org.bukkit.craftbukkit.v1_8_R3.entity.CraftPlayer");
            getHandle = craftPlayer.getMethod("getHandle");

            Class<?> entityPlayer = Class.forName("net.minecraft.server.v1_8_R3.EntityPlayer");
            connField = entityPlayer.getField("playerConnection");

            Class<?> playerConn = Class.forName("net.minecraft.server.v1_8_R3.PlayerConnection");
            sendPacket = playerConn.getMethod("sendPacket", packet);

            Class<?> ser = Class.forName(
                    "net.minecraft.server.v1_8_R3.IChatBaseComponent$ChatSerializer");
            fromJson = ser.getMethod("a", String.class);
        } catch (Throwable ignored) { }
        CHAT_PACKET_CTOR = ctor;
        GET_HANDLE       = getHandle;
        SEND_PACKET      = sendPacket;
        FROM_JSON        = fromJson;
        CONNECTION_FIELD = connField;
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
        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player == null || !player.isOnline()) continue;
            if (!profile.active() && !this.showWhenDormant) continue;
            try { sendActionBar(player, this.indicator); }
            catch (Throwable ignored) { }
        }
    }

    private static void sendActionBar(Player player, String text) {
        try {
            Class<?> spigot = Class.forName("org.bukkit.entity.Player$Spigot");
            Class<?> type   = Class.forName("net.md_5.bungee.api.ChatMessageType");
            Method m = spigot.getMethod("sendMessage", type, BaseComponent[].class);
            @SuppressWarnings({"unchecked", "rawtypes"})
            Object actionBar = Enum.valueOf((Class<? extends Enum>) type, "ACTION_BAR");
            m.invoke(player.spigot(), actionBar, TextComponent.fromLegacyText(text));
            return;
        } catch (Throwable ignored) { }

        if (CHAT_PACKET_CTOR == null || GET_HANDLE == null
                || SEND_PACKET == null || CONNECTION_FIELD == null) {
            return;
        }
        try {
            Object handle = GET_HANDLE.invoke(player);
            String json = ComponentSerializer.toString(TextComponent.fromLegacyText(text));
            Object component = FROM_JSON.invoke(null, json);
            Object packet = CHAT_PACKET_CTOR.newInstance(component, (byte) 2);
            Object connection = CONNECTION_FIELD.get(handle);
            SEND_PACKET.invoke(connection, packet);
        } catch (Throwable ignored) { }
    }
}
'''

JAVA_WORLD_RULES = r'''package com.yourname.nick.disguise;

import java.util.logging.Logger;
import org.bukkit.configuration.ConfigurationSection;

/**
 * World restrictions removed. Nicknames are active everywhere the moment
 * they are applied.
 */
public final class WorldRules {

    private static final WorldRules INSTANCE = new WorldRules();

    private WorldRules() { }

    public static WorldRules fromConfig(ConfigurationSection config, Logger logger) {
        return INSTANCE;
    }

    public boolean isActive(String worldName) {
        return true;
    }
}
'''

JAVA_GUI_CONFIG = r'''package com.yourname.nick.gui;

import java.io.File;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/** Typed reader for gui.yml. Every returned string is colour-translated. */
public final class GuiConfig {

    public static final class Button {
        private final String label;
        private final String command;
        private final String hover;
        public Button(String label, String command, String hover) {
            this.label = colorize(label);
            this.command = command == null ? "" : command;
            this.hover = colorize(hover);
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

    public String title()  { return colorize(this.yaml.getString("book.title",  "Nickname Setup")); }
    public String author() { return colorize(this.yaml.getString("book.author", "MineStormNickSystem")); }
    public String get(String path) { return colorize(this.yaml.getString(path, "")); }
    public List<String> list(String path) { return colorizeList(this.yaml.getStringList(path)); }
    public List<String> body(String page) { return colorizeList(this.yaml.getStringList(page + ".body")); }
    public List<String> footer(String page) { return colorizeList(this.yaml.getStringList(page + ".footer")); }

    public ChatColor color(String page) {
        String raw = this.yaml.getString(page + "-color", "BLACK");
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return ChatColor.BLACK; }
    }
    public ChatColor style(String page) {
        String raw = this.yaml.getString(page + "-style", "");
        if (raw == null || raw.isEmpty()) return null;
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return null; }
    }

    public Button button(String key) {
        String b = "buttons." + key + ".";
        return new Button(this.yaml.getString(b + "label", ""),
                          this.yaml.getString(b + "command", ""),
                          this.yaml.getString(b + "hover", ""));
    }
    public Button entry(String page, String key) {
        String b = page + ".entries." + key + ".";
        return new Button(this.yaml.getString(b + "label", ""), "",
                          this.yaml.getString(b + "hover", ""));
    }
    public Button pageButton(String page, String key) {
        String b = page + ".buttons." + key + ".";
        return new Button(this.yaml.getString(b + "label", ""), "",
                          this.yaml.getString(b + "hover", ""));
    }

    public static String colorize(String s) {
        return ChatColor.translateAlternateColorCodes('&', s == null ? "" : s);
    }
    private static List<String> colorizeList(List<String> in) {
        if (in == null) return Collections.emptyList();
        java.util.List<String> out = new java.util.ArrayList<String>(in.size());
        for (String s : in) out.add(colorize(s));
        return out;
    }
    public String format(String raw, String... pairs) {
        if (raw == null) return "";
        String out = raw;
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            out = out.replace("%" + pairs[i] + "%",
                              pairs[i + 1] == null ? "" : pairs[i + 1]);
        }
        return colorize(out);
    }
}
'''

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
                          Messages messages, GuiConfig gui,
                          DisguiseManager disguises, SkinCacheManager skins,
                          NameGenerator generator, NameValidator validator,
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
        else if ("close".equals(sub))  { }
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

    private void showIntro(Player player) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line("\u00a73\u00a7lMineStorm Nickname Setup"));
        out.add(blank());
        GuiConfig.Button b = gui.button("start");
        out.add(button(b.label(), b.command(), b.hover()));
        openBook(player, out);
    }
    private void showRankPicker(Player player) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("rank")) out.add(line(raw));
        for (Rank r : Rank.values()) {
            GuiConfig.Button e = gui.entry("rank", r.name());
            String label = empty(e.label()) ? "\u00a78\u27a4 \u00a77" + r.label() : e.label();
            String hover = empty(e.hover()) ? "Use " + r.label() : e.hover();
            out.add(button(label, "/nick ui rank " + r.name(), hover));
        }
        openBook(player, out);
    }
    private void showSkin(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("skin")) out.add(line(raw));
        addEntry(out, "skin", "normal",  "/nick ui skin normal");
        addEntry(out, "skin", "default", "/nick ui skin default");
        addEntry(out, "skin", "random",  "/nick ui skin random");
        if (session.history() != null) addEntry(out, "skin", "reuse", "/nick ui skin reuse");
        openBook(player, out);
    }
    private void showName(Player player, NickSession session) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("name")) out.add(line(raw));
        addEntry(out, "name", "random", "/nick ui name random");
        if (session.history() != null) addEntry(out, "name", "reuse", "/nick ui name reuse");
        for (String raw : gui.footer("name")) out.add(line(raw));
        openBook(player, out);
    }
    private void showRolledName(Player player, NickSession session) {
        String name = session.pendingName();
        if (name == null) { showName(player, session); return; }
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("rolled")) out.add(line(gui.format(raw, "name", name)));
        GuiConfig.Button use   = gui.pageButton("rolled", "use");
        GuiConfig.Button again = gui.pageButton("rolled", "again");
        out.add(button(empty(use.label()) ? "\u00a7a\u00a7l[USE NAME]" : use.label(),
                "/nick ui use",
                gui.format(empty(use.hover()) ? "Nick as %name%" : use.hover(), "name", name)));
        out.add(button(empty(again.label()) ? "\u00a7c\u00a7l[TRY AGAIN]" : again.label(),
                "/nick ui reroll",
                empty(again.hover()) ? "Generate a different name" : again.hover()));
        openBook(player, out);
    }
    private void showFinished(Player player, String nick) {
        Rank rank = Rank.DEFAULT;
        Optional<DisguiseProfile> prof = disguises.profile(player.getUniqueId());
        if (prof.isPresent()) rank = prof.get().rank();
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("done")) {
            out.add(line(gui.format(raw,
                    "name", nick, "rank", rank.label(), "player", player.getName())));
        }
        openBook(player, out);
    }

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
        if ("normal".equals(choice))       session.skin(SkinData.normal());
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

    private void addEntry(List<BaseComponent> out, String page, String key, String command) {
        GuiConfig.Button e = gui.entry(page, key);
        String label = empty(e.label()) ? ("\u00a78\u27a4 \u00a77" + key) : e.label();
        String hover = empty(e.hover()) ? key : e.hover();
        out.add(button(label, command, hover));
    }
    private void openBook(Player player, List<BaseComponent> out) {
        BaseComponent[] page = out.toArray(new BaseComponent[out.size()]);
        ItemStack book = VirtualBook.buildComponents(gui.title(), gui.author(), page);
        VirtualBook.open(player, book, page);
    }
    private static boolean empty(String s) { return s == null || s.isEmpty(); }
    private static BaseComponent blank() {
        return new TextComponent(TextComponent.fromLegacyText("\n"));
    }
    private static BaseComponent line(String raw) {
        return new TextComponent(TextComponent.fromLegacyText(
                (raw == null ? "" : raw) + "\n"));
    }
    private static BaseComponent button(String label, String command, String hover) {
        TextComponent c = new TextComponent(
                TextComponent.fromLegacyText("\u00a7a" + label + "\n"));
        c.setClickEvent(new ClickEvent(ClickEvent.Action.RUN_COMMAND, command));
        c.setHoverEvent(new HoverEvent(HoverEvent.Action.SHOW_TEXT,
                TextComponent.fromLegacyText("\u00a77" + hover)));
        return c;
    }
}
'''

JAVA_PACKET_MANAGER = r'''package com.yourname.nick.packet;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;

public final class PacketManager {

    private final MineStormNickPlugin plugin;
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
    private Class<?> chatComponentClass;
    private Method getHandleMethod;
    private Field  playerConnectionField;
    private Method sendPacketMethod;
    private Method getProfileMethod;
    private Method getIdMethod;
    private Method setLocationMethod;
    private Method spawnInMethod;
    private boolean enabled = false;

    public PacketManager(MineStormNickPlugin plugin, DisguiseRegistry registry) {
        this.plugin = plugin;
        this.registry = registry;
    }

    public void load() { }

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
            this.chatComponentClass    = Class.forName(pkg + "ChatComponentText");

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

    public void disable() { this.enabled = false; }

    public void refreshTabList(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) return;
        try {
            Object handle = this.getHandleMethod.invoke(target);
            String nick = resolveNick(target);
            if (nick == null || nick.isEmpty()) return;

            Field listName = findField(handle.getClass(), "listName");
            if (listName != null) {
                listName.setAccessible(true);
                Object component = this.chatComponentClass
                        .getConstructor(String.class).newInstance(nick);
                listName.set(handle, component);
            }
            Object profile = this.getProfileMethod.invoke(handle);
            if (profile != null) {
                try {
                    Method setName = profile.getClass().getMethod("setName", String.class);
                    setName.setAccessible(true);
                    setName.invoke(profile, nick);
                } catch (Throwable ignored) { }
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
        if (!this.enabled || target == null || !target.isOnline()) return;
        if (this.spawnInMethod == null) { refreshTabList(target); return; }
        try {
            Object handle = this.getHandleMethod.invoke(target);
            int entityId = (Integer) this.getIdMethod.invoke(handle);
            Object destroyPacket = this.packetDestroyClass
                    .getConstructor(int[].class)
                    .newInstance((Object) new int[] { entityId });
            Object world = target.getWorld();
            Object worldServer = world.getClass().getMethod("getHandle").invoke(world);
            if (this.setLocationMethod != null) {
                this.setLocationMethod.invoke(handle,
                        target.getLocation().getX(), target.getLocation().getY(),
                        target.getLocation().getZ(), target.getLocation().getYaw(),
                        target.getLocation().getPitch());
            }
            if (this.spawnInMethod.getParameterTypes().length == 1) {
                this.spawnInMethod.invoke(handle, worldServer);
            } else {
                this.spawnInMethod.invoke(handle);
            }
            Object spawnPacket = this.packetSpawnClass
                    .getConstructor(this.entityHumanClass).newInstance(handle);
            for (Player viewer : Bukkit.getOnlinePlayers()) {
                if (viewer.equals(target)) continue;
                sendPacket(viewer, destroyPacket);
                sendPacket(viewer, spawnPacket);
            }
            refreshTabList(target);
        } catch (Throwable t) {
            this.plugin.getLogger().warning("refreshNametag failed: " + t);
        }
    }

    public void resendOwnEntry(Player player) {
        if (player == null || !player.isOnline()) return;
        refreshTabList(player);
        refreshNametag(player);
    }

    private static Method tryGetMethod(Class<?> clazz, String name, Class<?>... params) {
        try {
            Method m = clazz.getMethod(name, params);
            m.setAccessible(true);
            return m;
        } catch (NoSuchMethodException e) { return null; }
    }
    private static Field findField(Class<?> clazz, String name) {
        Class<?> c = clazz;
        while (c != null) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f;
            } catch (NoSuchFieldException ignored) { c = c.getSuperclass(); }
        }
        return null;
    }
    private String resolveNick(Player player) {
        DisguiseProfile profile = this.registry.get(player.getUniqueId()).orElse(null);
        return profile == null ? null : profile.nickname();
    }
    @SuppressWarnings({"unchecked", "rawtypes"})
    private Object enumAction(String name) throws Exception {
        return Enum.valueOf((Class<? extends Enum>) this.enumPlayerInfoActionClass, name);
    }
    private Object buildInfoPacket(Object action, List<Object> players) throws Exception {
        for (java.lang.reflect.Constructor<?> ctor : this.packetInfoClass.getConstructors()) {
            Class<?>[] params = ctor.getParameterTypes();
            if (params.length == 2 && params[0] == this.enumPlayerInfoActionClass
                    && Iterable.class.isAssignableFrom(params[1])) {
                return ctor.newInstance(action, players);
            }
        }
        if (!players.isEmpty()) {
            for (java.lang.reflect.Constructor<?> ctor : this.packetInfoClass.getConstructors()) {
                Class<?>[] params = ctor.getParameterTypes();
                if (params.length == 2 && params[0] == this.enumPlayerInfoActionClass
                        && params[1] == this.entityPlayerClass) {
                    return ctor.newInstance(action, players.get(0));
                }
            }
        }
        throw new IllegalStateException("No usable PacketPlayOutPlayerInfo ctor");
    }
    private void broadcast(Object packet) throws Exception {
        for (Player online : Bukkit.getOnlinePlayers()) sendPacket(online, packet);
    }
    private void sendPacket(Player player, Object packet) throws Exception {
        Object handle = this.getHandleMethod.invoke(player);
        Object connection = this.playerConnectionField.get(handle);
        this.sendPacketMethod.invoke(connection, packet);
    }
}
'''

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
'''

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
            return this.plugin.getServer().getPluginManager().isPluginEnabled("LuckPerms");
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
            player.sendMessage(ChatColor.RED + "You need the " + ChatColor.GOLD
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
    public List<String> onTabComplete(CommandSender s, Command c, String a, String[] args) {
        return Collections.emptyList();
    }
}
'''

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
    public List<String> onTabComplete(CommandSender s, Command c, String a, String[] args) {
        if (args.length == 1) {
            String typed = args[0].toLowerCase(Locale.ROOT);
            if ("reload".startsWith(typed)) return Arrays.asList("reload");
        }
        return Collections.emptyList();
    }
}
'''

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
    private BukkitTask       actionBarTask;
    private BukkitTask       pruneTask;

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

        bind("nick",                new NickCommand(this, this.messages, this.bookGui,
                                                    this.disguises, this.skins, this.validator));
        bind("realname",            new RealNameCommand(this, this.messages,
                                                        this.registry, this.storage));
        bind("minestormnicksystem", new MineStormNickSystemCommand(this));
        bind("g",                   new GlobalCommand(this, this.messages, this.luckPerms));

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

    private void scheduleTasks() {
        if (getConfig().getBoolean("actionbar.enabled", true)) {
            long interval = Math.max(10L, getConfig().getLong("actionbar.interval-ticks", 40L));
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

settings:
  persist-across-sessions: true
  rewrite-chat: true
  rewrite-join-quit: true

# World restrictions were removed. Nicknames apply instantly, everywhere.

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
# The fixer writes enabled=true/false automatically based on what it
# detects on disk.
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
# gui.yml - strings shown inside the /nick setup book.
# Hot-reloadable with /minestormnicksystem reload.
# -----------------------------------------------------------------------------

book:
  title:  "Nickname Setup"
  author: "MineStormNickSystem"

rank:
  title: ""
  body:
    - "&0Let's get you set up with your nickname!"
    - "&0First, you'll need to choose which &lRANK&r&0 you would like to be shown as when nicked."
    - ""
  entries:
    DEFAULT:
      label: "&8> &7DEFAULT"
      hover: "Play as the default rank"
    VIP:
      label: "&8> &aVIP"
      hover: "Play as VIP"
    VIP_PLUS:
      label: "&8> &aVIP&6+"
      hover: "Play as VIP+"
    MVP:
      label: "&8> &bMVP"
      hover: "Play as MVP"
    MVP_PLUS:
      label: "&8> &bMVP&c+"
      hover: "Play as MVP+"

skin:
  title: ""
  body:
    - "&0Awesome! Now, which &lSKIN&r&0 would you like to have while nicked?"
    - ""
  entries:
    normal:
      label: "&8> &1My normal skin"
      hover: "Keep your own skin"
    default:
      label: "&8> &1Steve/Alex skin"
      hover: "Use the default Steve/Alex skin"
    random:
      label: "&8> &1Random skin"
      hover: "Pick a random skin from the pool"
    reuse:
      label: "&8> &1Reuse [Previous Skin]"
      hover: "Use the skin from your last nickname"

name:
  title: ""
  body:
    - "&0Alright, now you'll need to choose the &lNAME&r&0 to use!"
    - ""
  entries:
    random:
      label: "&8> &1Use a random name"
      hover: "Generate a random username"
    reuse:
      label: "&8> &1Reuse [Previous Name]"
      hover: "Use the name from your last nickname"
  footer:
    - ""
    - "&0To go back to being your usual self, type:"
    - "&c/nick reset"

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

done:
  title: ""
  body:
    - "&0You have finished setting up your nickname!"
    - ""
    - "&0You are now nicked as &8[&7%rank%&8] &7%name%&0."
    - ""
    - "&0To go back to being your usual self, type:"
    - "&c/nick reset"

buttons:
  start:
    label: "&a[ Start setup ]"
    command: "/nick ui rank"
    hover: "Begin the setup"
'''

RES_MESSAGES_YML = r'''# MineStormNickSystem messages (legacy colour codes).

prefix: "&8[&6MineStorm&8] &r"

player-only: "&cThis command can only be used by players."
usage: "&cUsage: /nick, /nick reset, /nick skin [player], /nick name [name]"
no-permission: "&cYou do not have permission to do that."
session-expired: "&cThat nickname setup has expired. Type &e/nick &cto start again."
storage-error: "&cThe nickname database is unavailable right now. Please try again shortly."

nick-finished: "&aYou have finished setting up your nickname! You will be nicked as &8[&7%rank%&8] &7%name%&a."
nick-reset: "&aYou are back to being your usual self."
nick-not-nicked: "&cYou do not currently have a nickname."

# Displayed ONLY in the action bar - never in chat.
actionbar: "&aYou are currently &lNICKED&r&a."

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

RES_NAMES_YML = r'''# Name rules and the random-name generator pool.

generator:
  max-number: 99
  adjectives:
    - Swift
    - Quiet
    - Brave
    - Cosmic
    - Frosty
    - Lucky
    - Mighty
    - Shadow
    - Golden
    - Silent
    - Crimson
    - Hidden
    - Wild
    - Clever
    - Rapid
    - Amber
    - Misty
    - Stormy
    - Pixel
    - Lunar
  nouns:
    - Fox
    - Panda
    - Falcon
    - Tiger
    - Otter
    - Wolf
    - Comet
    - Ranger
    - Pilot
    - Knight
    - Badger
    - Raven
    - Dolphin
    - Hunter
    - Wizard
    - Turtle
    - Phoenix
    - Sparrow
    - Lynx
    - Gecko

reserved:
  - Notch
  - jeb_
  - Dinnerbone
  - Herobrine
  - Entity303
  - Steve
  - Alex
  - Admin
  - Administrator
  - Owner
  - Moderator
  - Console
  - Server
  - Staff

reserved-fragments:
  - admin
  - moderator
  - owner
  - staff
  - server
  - console
  - herobrine
'''


# ═══════════════════════════════════════════════════════════════════════════
#  pom.xml patcher
# ═══════════════════════════════════════════════════════════════════════════

SQLITE_DEP_BLOCK = """        <!-- Modern SQLite driver (Java 8) shaded under a private package
             so it never clashes with the 3.7.2 copy inside Spigot 1.8.8. -->
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

    if "sqlite-jdbc" not in new:
        idx = new.rfind("</dependencies>")
        if idx < 0:
            log("WARN", "pom.xml has no </dependencies>; cannot add sqlite-jdbc")
        else:
            new = new[:idx] + SQLITE_DEP_BLOCK + new[idx:]
            changed = True

    if "<relocations>" not in new:
        anchor = "<createDependencyReducedPom>false</createDependencyReducedPom>"
        idx = new.find(anchor)
        if idx < 0:
            log("WARN", "pom.xml shade-plugin anchor missing; cannot add relocation")
        else:
            at = idx + len(anchor)
            new = new[:at] + "\n" + SHADE_RELOCATION_BLOCK.rstrip() + new[at:]
            changed = True

    if not changed:
        log("SKIP", "pom.xml already patched")
        return
    write_text(pom, new, dry=dry, backup=backup)


# ═══════════════════════════════════════════════════════════════════════════
#  Rename helper for existing Java sources
# ═══════════════════════════════════════════════════════════════════════════

def rename_references(src: str) -> str:
    src = src.replace("NickPlugin", "MineStormNickPlugin")
    src = src.replace("MineStormMineStormNickPlugin", "MineStormNickPlugin")
    src = src.replace("NickSystemCommand", "MineStormNickSystemCommand")
    src = src.replace("/nicksystem", "/minestormnicksystem")
    src = src.replace("nicksystem.admin", "minestormnicksystem.admin")
    src = src.replace("nicksystem.global", "minestormnicksystem.global")
    src = src.replace('"NickSystem"', '"MineStormNickSystem"')
    return src


CANONICAL_FILES = {
    PACKAGE_DIR / "MineStormNickPlugin.java",
    PACKAGE_DIR / "task" / "ActionBarTask.java",
    PACKAGE_DIR / "packet" / "PacketManager.java",
    PACKAGE_DIR / "gui" / "GuiConfig.java",
    PACKAGE_DIR / "gui" / "BookGUIManager.java",
    PACKAGE_DIR / "integration" / "LuckPermsHook.java",
    PACKAGE_DIR / "disguise" / "WorldRules.java",
    PACKAGE_DIR / "storage" / "StorageManager.java",
    PACKAGE_DIR / "command" / "GlobalCommand.java",
    PACKAGE_DIR / "command" / "MineStormNickSystemCommand.java",
}


def rename_existing_java_files(dry: bool, backup: bool) -> None:
    for path in SRC_JAVA.rglob("*.java"):
        if path in CANONICAL_FILES:
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
#  Server-side copy refresher
# ═══════════════════════════════════════════════════════════════════════════

SERVER_FILES = {
    "messages.yml": RES_MESSAGES_YML,
    "config.yml":   RES_CONFIG_YML,
    "gui.yml":      RES_GUI_YML,
}

SERVER_DIR_NAMES = ["plugins/MineStormNickSystem", "plugins/NickSystem"]


def find_server_dirs() -> list[Path]:
    found: list[Path] = []
    for base in [ROOT, *ROOT.parents]:
        for rel in SERVER_DIR_NAMES:
            candidate = base / rel
            if candidate.is_dir() and candidate not in found:
                found.append(candidate)
    return found


def refresh_server_copies(dry: bool, backup: bool) -> None:
    for d in find_server_dirs():
        for filename, content in SERVER_FILES.items():
            write_text(d / filename, content, dry=dry, backup=backup)


# ═══════════════════════════════════════════════════════════════════════════
#  LuckPerms detection
# ═══════════════════════════════════════════════════════════════════════════

def detect_luckperms() -> tuple[bool, str]:
    """
    Scans for a LuckPerms installation on disk.

    Looks in plugins/LuckPerms/ and plugins/LuckPerms*.jar, walking up
    from the source root for up to four levels so the script finds the
    server folder even when run from inside the source tree.
    """
    search_roots: list[Path] = []
    for base in [ROOT, *ROOT.parents]:
        search_roots.append(base)
        if len(search_roots) >= 4:
            break

    for base in search_roots:
        plugins = base / "plugins"
        if not plugins.is_dir():
            continue

        lp_dir = plugins / "LuckPerms"
        if lp_dir.is_dir():
            config = lp_dir / "config.yml"
            extra = " (config.yml present)" if config.is_file() else ""
            return True, f"{lp_dir.relative_to(base)}{extra}"

        for jar in sorted(plugins.glob("LuckPerms*.jar")):
            return True, str(jar.relative_to(base))

        for child in plugins.iterdir():
            if child.is_dir() and child.name.lower() == "luckperms":
                return True, str(child.relative_to(base))
            if child.suffix.lower() == ".jar" and child.stem.lower().startswith("luckperms"):
                return True, str(child.relative_to(base))

    return False, "not found"


def _is_under_luckperms(text: str, pos: int) -> bool:
    """True if the line at pos belongs to the top-level luckperms: block."""
    head = text[:pos]
    last_lp = head.rfind("\nluckperms:")
    if last_lp < 0:
        return False
    tail = head[last_lp:]
    for line in tail.splitlines()[1:]:
        stripped = line.strip()
        if stripped and not line.startswith(" ") and not line.startswith("\t") \
                and ":" in stripped:
            return False
    return True


def apply_luckperms_flag(lp_found: bool, dry: bool, backup: bool) -> None:
    """
    Rewrites luckperms.enabled in every installed server copy of config.yml
    (if any) so it matches the actual presence of LuckPerms on disk.
    Silently does nothing when no server folder exists.
    """
    dirs = find_server_dirs()
    if not dirs:
        return
    desired = "true" if lp_found else "false"
    for d in dirs:
        cfg = d / "config.yml"
        if not cfg.is_file():
            continue
        text = cfg.read_text(encoding="utf-8")
        if "luckperms:" not in text:
            continue
        new_text = re.sub(
            r"^(\s*enabled:\s*)(true|false)(\s*(?:#.*)?)$",
            lambda m: (m.group(1) + desired + m.group(3))
            if _is_under_luckperms(text, m.start()) else m.group(0),
            text, flags=re.MULTILINE,
        )
        if new_text != text:
            write_text(cfg, new_text, dry=dry, backup=backup)
            log("OK  ", f"set luckperms.enabled={desired} in "
                        f"{cfg.relative_to(ROOT)}")


# ═══════════════════════════════════════════════════════════════════════════
#  File maps + verification
# ═══════════════════════════════════════════════════════════════════════════

JAVA_FILES = {
    PACKAGE_DIR / "MineStormNickPlugin.java":                    JAVA_MAIN,
    PACKAGE_DIR / "task" / "ActionBarTask.java":                 JAVA_ACTIONBAR,
    PACKAGE_DIR / "packet" / "PacketManager.java":               JAVA_PACKET_MANAGER,
    PACKAGE_DIR / "gui" / "GuiConfig.java":                      JAVA_GUI_CONFIG,
    PACKAGE_DIR / "gui" / "BookGUIManager.java":                 JAVA_BOOK_GUI,
    PACKAGE_DIR / "integration" / "LuckPermsHook.java":          JAVA_LUCKPERMS_HOOK,
    PACKAGE_DIR / "disguise" / "WorldRules.java":                JAVA_WORLD_RULES,
    PACKAGE_DIR / "storage" / "StorageManager.java":             JAVA_STORAGE_MANAGER,
    PACKAGE_DIR / "command" / "GlobalCommand.java":              JAVA_GLOBAL_COMMAND,
    PACKAGE_DIR / "command" / "MineStormNickSystemCommand.java": JAVA_RELOAD_COMMAND,
}

RESOURCE_FILES = {
    RESOURCES / "plugin.yml":   RES_PLUGIN_YML,
    RESOURCES / "config.yml":   RES_CONFIG_YML,
    RESOURCES / "gui.yml":      RES_GUI_YML,
    RESOURCES / "messages.yml": RES_MESSAGES_YML,
    RESOURCES / "names.yml":    RES_NAMES_YML,
}


def verify_sentinels() -> bool:
    checks = {
        PACKAGE_DIR / "task" / "ActionBarTask.java":
            ["PacketPlayOutChat", "(byte) 2"],
        PACKAGE_DIR / "disguise" / "WorldRules.java":
            ["return true;"],
        PACKAGE_DIR / "storage" / "StorageManager.java":
            ["SELECT 1", "runWithRetry"],
        PACKAGE_DIR / "packet" / "PacketManager.java":
            ["UPDATE_DISPLAY_NAME", "listName"],
        PACKAGE_DIR / "MineStormNickPlugin.java":
            ["minestormnicksystem", "reloadEverything"],
        RESOURCES / "plugin.yml":   ["minestormnicksystem:", "msns", "  g:"],
        RESOURCES / "config.yml":   ["luckperms:", "actionbar:"],
        RESOURCES / "gui.yml":      ["rank:", "done:", "buttons:"],
        RESOURCES / "messages.yml": ["actionbar:"],
        RESOURCES / "names.yml":    ["generator:", "reserved:"],
        ROOT / "pom.xml":           ["sqlite-jdbc", "<relocations>"],
    }
    ok = True
    for path, needles in checks.items():
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

    # Detect LuckPerms before writing config.yml so the flag is ready.
    lp_found, lp_evidence = detect_luckperms()
    if lp_found:
        log("INFO", f"LuckPerms detected: {lp_evidence}")
    else:
        log("INFO", "LuckPerms not detected - /g will fall back to "
                    "permission nodes (group.prime, minestormnicksystem.global)")

    rename_existing_java_files(args.dry_run, backup)

    for path, content in {**JAVA_FILES, **RESOURCE_FILES}.items():
        result = write_text(path, content, dry=args.dry_run, backup=backup)
        if result == "created":   CREATED.append(str(path.relative_to(ROOT)))
        elif result == "updated": UPDATED.append(str(path.relative_to(ROOT)))
        else:                     SKIPPED.append(str(path.relative_to(ROOT)))

    old_cmd = PACKAGE_DIR / "command" / "NickSystemCommand.java"
    if old_cmd.exists():
        if args.dry_run:
            log("DRY ", f"would delete {old_cmd.relative_to(ROOT)}")
        else:
            try:
                old_cmd.unlink()
                DELETED.append(str(old_cmd.relative_to(ROOT)))
                log("OK  ", f"deleted {old_cmd.relative_to(ROOT)}")
            except OSError as exc:
                log("WARN", f"could not delete {old_cmd}: {exc}")

    patch_pom(args.dry_run, backup)
    refresh_server_copies(args.dry_run, backup)
    apply_luckperms_flag(lp_found, args.dry_run, backup)

    if not args.dry_run:
        print()
        log("CHK ", "verifying sentinels")
        if verify_sentinels():
            log("CHK ", "all sentinels present")

    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"  LuckPerms      : {'FOUND - ' + lp_evidence if lp_found else 'not installed'}")
    print(f"  created        : {len(CREATED)}")
    for p in CREATED: print(f"    + {p}")
    print(f"  updated        : {len(UPDATED)}")
    for p in UPDATED: print(f"    ~ {p}")
    print(f"  deleted        : {len(DELETED)}")
    for p in DELETED: print(f"    - {p}")
    print(f"  skipped        : {len(SKIPPED)}")
    for p in SKIPPED: print(f"    = {p}")
    print()
    if args.dry_run:
        print("Dry-run complete. Re-run without --dry-run to apply.")
    else:
        print("Rebuild:  mvn -B clean package")
        print("Then STOP the server fully and start it again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())