#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py — Refactor for MineStormNickSystem
============================================

این اسکریپت این کارها رو انجام می‌ده:

  1. کل سیستم Rank رو حذف می‌کنه (Rank.java و همه‌ی ارجاع‌ها).
  2. Nickname بلافاصله در همه‌ی دنیاها ست می‌شه (بدون محدودیت).
  3. پیام اشتباه نسخه (1.19.3) رو در MineStormNickPlugin اصلاح می‌کنه.
  4. gui.yml رو از بخش rank پاک می‌کنه و دکمه‌ی Start رو مستقیم به skin وصل می‌کنه.
  5. StorageManager رو طوری بازنویسی می‌کنه که با دیتابیس‌های قدیمی
     (که ستون rank_used دارن) سازگار بمونه بدون اینکه Rank توی کد باشه.

اجرا: پایتون رو در ریشه پروژه (کنار pom.xml) بذار و اجرا کن:  python fixer.py
"""

import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
JAVA = os.path.join(BASE, "src", "main", "java", "com", "yourname", "nick")
RES  = os.path.join(BASE, "src", "main", "resources")


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def write(rel_path, content):
    path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"  [WRITE] {rel_path}")


def delete(rel_path):
    path = os.path.join(BASE, rel_path)
    if os.path.exists(path):
        os.remove(path)
        print(f"  [DELETE] {rel_path}")
    else:
        print(f"  [SKIP]   {rel_path} (not present)")


def patch(rel_path, old, new, required=True):
    path = os.path.join(BASE, rel_path)
    if not os.path.exists(path):
        print(f"  [WARN]   {rel_path} not found")
        return
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if old not in src:
        if required:
            print(f"  [WARN]   pattern not found in {rel_path}")
        return
    src = src.replace(old, new)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print(f"  [PATCH]  {rel_path}")


# =========================================================================== #
#  1) Remove Rank.java
# =========================================================================== #
print("\n[1/9] Removing Rank system ...")
delete("src/main/java/com/yourname/nick/model/Rank.java")


# =========================================================================== #
#  2) DisguiseProfile.java
# =========================================================================== #
print("\n[2/9] Rewriting DisguiseProfile.java ...")
write("src/main/java/com/yourname/nick/model/DisguiseProfile.java", r"""package com.yourname.nick.model;

import java.util.UUID;

/**
 * Immutable snapshot of a player's current nickname state.
 * The Rank concept was removed entirely; the visible name is now
 * exactly the nickname that was chosen.
 */
public final class DisguiseProfile {

    private final UUID realUuid;
    private final String realName;
    private final String nickname;
    private final SkinData skin;
    private final int stars;
    private final boolean active;
    private final String originalDisplayName;

    public DisguiseProfile(UUID realUuid,
                           String realName,
                           String nickname,
                           SkinData skin,
                           int stars,
                           boolean active,
                           String originalDisplayName) {
        this.realUuid = realUuid;
        this.realName = realName;
        this.nickname = nickname;
        this.skin = skin;
        this.stars = stars;
        this.active = active;
        this.originalDisplayName = originalDisplayName;
    }

    public UUID realUuid()             { return this.realUuid; }
    public String realName()           { return this.realName; }
    public String nickname()           { return this.nickname; }
    public SkinData skin()             { return this.skin; }
    public int stars()                 { return this.stars; }
    public boolean active()            { return this.active; }
    public String originalDisplayName(){ return this.originalDisplayName; }

    /* Legacy-style getters kept for binary compatibility. */
    public UUID getRealUuid()              { return this.realUuid; }
    public String getRealName()            { return this.realName; }
    public String getNickname()            { return this.nickname; }
    public SkinData getSkin()              { return this.skin; }
    public int getStars()                  { return this.stars; }
    public boolean isActive()              { return this.active; }
    public String getOriginalDisplayName() { return this.originalDisplayName; }

    public DisguiseProfile withActive(boolean newActive) {
        return new DisguiseProfile(this.realUuid, this.realName, this.nickname,
                this.skin, this.stars, newActive, this.originalDisplayName);
    }

    public DisguiseProfile withSkin(SkinData newSkin) {
        return new DisguiseProfile(this.realUuid, this.realName, this.nickname,
                newSkin, this.stars, this.active, this.originalDisplayName);
    }

    /** The display name is simply the nickname now. */
    public String styledName() {
        return this.nickname;
    }
}
""")


# =========================================================================== #
#  3) NickRecord.java
# =========================================================================== #
print("\n[3/9] Rewriting NickRecord.java ...")
write("src/main/java/com/yourname/nick/model/NickRecord.java", r"""package com.yourname.nick.model;

import java.util.UUID;

/**
 * One persisted row of nick history. The Rank column is no longer
 * part of the API; older databases keep the column but its value is
 * ignored on read and written as "NONE" on insert (see StorageManager).
 */
public final class NickRecord {

    private final UUID realUuid;
    private final String realName;
    private final String nickname;
    private final String skinSource;
    private final String skinValue;
    private final String skinSignature;
    private final String action;
    private final long createdAt;
    private final String ip;

    public NickRecord(UUID realUuid,
                      String realName,
                      String nickname,
                      String skinSource,
                      String skinValue,
                      String skinSignature,
                      String action,
                      long createdAt,
                      String ip) {
        this.realUuid = realUuid;
        this.realName = realName;
        this.nickname = nickname;
        this.skinSource = skinSource;
        this.skinValue = skinValue;
        this.skinSignature = skinSignature;
        this.action = action;
        this.createdAt = createdAt;
        this.ip = ip;
    }

    public UUID realUuid()           { return this.realUuid; }
    public String realName()         { return this.realName; }
    public String nickname()         { return this.nickname; }
    public String skinSource()       { return this.skinSource; }
    public String skinValue()        { return this.skinValue; }
    public String skinSignature()    { return this.skinSignature; }
    public String action()           { return this.action; }
    public long createdAt()          { return this.createdAt; }
    public String ip()               { return this.ip; }

    /* Legacy getters. */
    public UUID getRealUuid()        { return this.realUuid; }
    public String getRealName()      { return this.realName; }
    public String getNickname()      { return this.nickname; }
    public String getSkinSource()    { return this.skinSource; }
    public String getSkinValue()     { return this.skinValue; }
    public String getSkinSignature() { return this.skinSignature; }
    public String getAction()        { return this.action; }
    public long getCreatedAt()       { return this.createdAt; }
    public String getIp()            { return this.ip; }

    public SkinData toSkinData() {
        return SkinData.fromStorage(this.skinSource, this.skinValue, this.skinSignature);
    }
}
""")


# =========================================================================== #
#  4) NickSession.java
# =========================================================================== #
print("\n[4/9] Rewriting NickSession.java ...")
write("src/main/java/com/yourname/nick/gui/NickSession.java", r"""package com.yourname.nick.gui;

import com.yourname.nick.model.NickRecord;
import com.yourname.nick.model.SkinData;

/**
 * Short-lived GUI session. The Rank step was removed; the flow is now
 * skin -> name -> (optional roller) -> apply.
 */
public final class NickSession {

    public enum Step { SKIN, NAME, ROLLER }

    private final NickRecord history;
    private Step step = Step.SKIN;
    private SkinData skin = SkinData.normal();
    private String pendingName;

    public NickSession(NickRecord history) {
        this.history = history;
    }

    public NickRecord history() { return this.history; }
    public Step step()          { return this.step; }
    public void step(Step s)    { this.step = s; }
    public SkinData skin()      { return this.skin; }
    public void skin(SkinData s){ this.skin = s; }
    public String pendingName() { return this.pendingName; }
    public void pendingName(String name) { this.pendingName = name; }
}
""")


# =========================================================================== #
#  5) BookGUIManager.java
# =========================================================================== #
print("\n[5/9] Rewriting BookGUIManager.java ...")
write("src/main/java/com/yourname/nick/gui/BookGUIManager.java", r"""package com.yourname.nick.gui;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseManager;
import com.yourname.nick.message.Messages;
import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
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
        if ("skin".equals(sub))        chooseSkin(player, session, args);
        else if ("name".equals(sub))   chooseName(player, session, args);
        else if ("use".equals(sub))    useRolledName(player, session);
        else if ("reroll".equals(sub)) rollName(player, session);
        else if ("close".equals(sub))  { /* no-op */ }
        else                           showIntro(player);
    }

    public void applyCustomName(Player player, String nick) {
        NickSession session = this.sessions.get(player.getUniqueId());
        Optional<DisguiseProfile> current = this.disguises.profile(player.getUniqueId());
        SkinData skin = session != null ? session.skin()
                : (current.isPresent() ? current.get().skin() : SkinData.normal());
        NameValidator.Result result = this.validator.validate(nick, player);
        if (result != NameValidator.Result.VALID) {
            showName(player, session != null ? session : new NickSession(null));
            return;
        }
        this.disguises.apply(player, nick, skin);
        this.sessions.remove(player.getUniqueId());
        showFinished(player, nick);
    }

    public void clearSession(UUID uuid) { this.sessions.remove(uuid); }
    public void clear()                 { this.sessions.clear(); }

    /* ------------------------------------------------------------------ */

    private void showIntro(Player player) {
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        out.add(line("\u00a73\u00a7lMineStorm Nickname Setup"));
        out.add(blank());
        GuiConfig.Button b = gui.button("start");
        out.add(button(b.label(), b.command(), b.hover()));
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
        List<BaseComponent> out = new ArrayList<BaseComponent>();
        for (String raw : gui.body("done")) {
            out.add(line(gui.format(raw,
                    "name", nick,
                    "player", player.getName())));
        }
        openBook(player, out);
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
        this.disguises.apply(player, nick, session.skin());
        this.sessions.remove(player.getUniqueId());
        showFinished(player, nick);
    }

    /* ------------------------------------------------------------------ */

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
""")


# =========================================================================== #
#  6) DisguiseManager.java
# =========================================================================== #
print("\n[6/9] Rewriting DisguiseManager.java ...")
write("src/main/java/com/yourname/nick/disguise/DisguiseManager.java", r"""package com.yourname.nick.disguise;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.integration.BedwarsLevelHook;
import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
import com.yourname.nick.model.SkinData;
import com.yourname.nick.packet.PacketManager;
import com.yourname.nick.storage.StorageManager;
import java.net.InetSocketAddress;
import java.util.Optional;
import java.util.UUID;
import java.util.function.BiConsumer;
import java.util.logging.Level;
import org.bukkit.entity.Player;

public final class DisguiseManager {

    private static final String ACTION_SET   = "SET";
    private static final String ACTION_RESET = "RESET";

    private final MineStormNickPlugin plugin;
    private final DisguiseRegistry registry;
    private final PacketManager packets;
    private final StorageManager storage;
    private final WorldRules rules;
    private final BedwarsLevelHook bedwars;

    public DisguiseManager(MineStormNickPlugin plugin,
                           DisguiseRegistry registry,
                           PacketManager packets,
                           StorageManager storage,
                           WorldRules rules,
                           BedwarsLevelHook bedwars) {
        this.plugin = plugin;
        this.registry = registry;
        this.packets = packets;
        this.storage = storage;
        this.rules = rules;
        this.bedwars = bedwars;
    }

    public Optional<DisguiseProfile> profile(UUID uuid) {
        return this.registry.get(uuid);
    }

    /** Apply a new nickname immediately, everywhere. */
    public void apply(Player player, String nick, SkinData skin) {
        DisguiseProfile profile = install(player, nick, skin, true);
        record(player, profile, ACTION_SET);
    }

    public void restore(final Player player, NickRecord stored) {
        install(player, stored.nickname(), stored.toSkinData(), false);
        this.plugin.getServer().getScheduler().runTaskLater(this.plugin,
                new Runnable() {
                    @Override
                    public void run() {
                        if (player.isOnline()
                                && DisguiseManager.this.registry.active(
                                        player.getUniqueId()) != null) {
                            DisguiseManager.this.refresh(player);
                        }
                    }
                }, 2L);
    }

    public boolean restorePending(Player player) {
        Optional<NickRecord> stored = this.registry.takePending(player.getUniqueId());
        if (stored.isPresent()) {
            restore(player, stored.get());
            return true;
        }
        return false;
    }

    public boolean reset(Player player) {
        DisguiseProfile removed = this.registry.remove(player.getUniqueId());
        if (removed == null) {
            return false;
        }
        player.setDisplayName(removed.originalDisplayName());
        refresh(player);
        record(player, removed, ACTION_RESET);
        return true;
    }

    public boolean changeSkin(Player player, SkinData skin) {
        Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
        if (!existing.isPresent()) {
            return false;
        }
        DisguiseProfile updated = existing.get().withSkin(skin);
        this.registry.put(updated);
        refresh(player);
        record(player, updated, ACTION_SET);
        return true;
    }

    public void onWorldChange(Player player) {
        Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
        if (!existing.isPresent()) {
            return;
        }
        DisguiseProfile current = existing.get();
        boolean shouldBeActive = this.rules.isActive(player.getWorld().getName());
        if (shouldBeActive == current.active()) {
            return;
        }
        DisguiseProfile updated = current.withActive(shouldBeActive);
        this.registry.put(updated);
        player.setDisplayName(shouldBeActive
                ? updated.styledName()
                : updated.originalDisplayName());
        refresh(player);
    }

    public void unload(Player player) {
        this.registry.remove(player.getUniqueId());
    }

    public void shutdown() {
        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player != null) {
                player.setDisplayName(profile.originalDisplayName());
            }
        }
        this.registry.clear();
    }

    /* ------------------------------------------------------------------ */
    /*  Internals                                                         */
    /* ------------------------------------------------------------------ */

    private DisguiseProfile install(Player player,
                                    String nick,
                                    SkinData skin,
                                    boolean refreshNow) {
        Optional<DisguiseProfile> previous = this.registry.get(player.getUniqueId());

        String original = previous.isPresent()
                ? previous.get().originalDisplayName()
                : player.getDisplayName();
        boolean active = this.rules.isActive(player.getWorld().getName());

        DisguiseProfile profile = new DisguiseProfile(
                player.getUniqueId(),
                player.getName(),
                nick,
                skin,
                this.bedwars.rollStars(),
                active,
                original);

        this.registry.put(profile);
        player.setDisplayName(active ? profile.styledName() : original);

        if (refreshNow) {
            refresh(player);
        }
        return profile;
    }

    private void refresh(final Player target) {
        if (target == null || !target.isOnline()) {
            return;
        }
        // Defer by one tick so the tab-list entry exists before we overwrite it.
        this.plugin.getServer().getScheduler().runTaskLater(this.plugin,
                new Runnable() {
                    @Override
                    public void run() {
                        if (!target.isOnline()) {
                            return;
                        }
                        packets.resendOwnEntry(target);
                    }
                }, 1L);
    }

    private void record(Player player, DisguiseProfile profile, String action) {
        InetSocketAddress address = player.getAddress();
        String ip = (address == null || address.getAddress() == null)
                ? "unknown"
                : address.getAddress().getHostAddress();

        NickRecord row = new NickRecord(
                profile.realUuid(),
                profile.realName(),
                profile.nickname(),
                profile.skin().sourceKey(),
                profile.skin().value(),
                profile.skin().signature(),
                action,
                System.currentTimeMillis(),
                ip);

        this.storage.insert(row).whenComplete(new BiConsumer<Void, Throwable>() {
            @Override
            public void accept(Void ignored, Throwable error) {
                if (error != null) {
                    plugin.getLogger().log(Level.SEVERE,
                            "Failed to persist nick action", error);
                }
            }
        });
    }
}
""")


# =========================================================================== #
#  7) NickPlaceholderExpansion.java
# =========================================================================== #
print("\n[7/9] Rewriting NickPlaceholderExpansion.java ...")
write("src/main/java/com/yourname/nick/integration/NickPlaceholderExpansion.java", r"""package com.yourname.nick.integration;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.util.Locale;
import java.util.Optional;
import me.clip.placeholderapi.PlaceholderAPI;
import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.OfflinePlayer;

public final class NickPlaceholderExpansion extends PlaceholderExpansion {

    private final MineStormNickPlugin plugin;
    private final DisguiseRegistry registry;
    private final BedwarsLevelHook bedwars;

    public NickPlaceholderExpansion(MineStormNickPlugin plugin,
                                    DisguiseRegistry registry,
                                    BedwarsLevelHook bedwars) {
        this.plugin = plugin;
        this.registry = registry;
        this.bedwars = bedwars;
    }

    @Override public String getIdentifier() { return "nick"; }
    @Override public String getAuthor() {
        return String.join(", ", this.plugin.getDescription().getAuthors());
    }
    @Override public String getVersion() {
        return this.plugin.getDescription().getVersion();
    }
    @Override public boolean persist() { return true; }

    @Override
    public String onRequest(OfflinePlayer player, String params) {
        if (player == null) return "";

        Optional<DisguiseProfile> profile = this.registry.get(player.getUniqueId());
        String realName = profile.isPresent()
                ? profile.get().realName()
                : (player.getName() == null ? "" : player.getName());

        String key = (params == null) ? "" : params.toLowerCase(Locale.ROOT);
        if ("realname".equals(key))    return realName;
        if ("nick".equals(key))        return profile.isPresent() ? profile.get().nickname() : "";
        if ("displayname".equals(key)) {
            return (profile.isPresent() && profile.get().active())
                    ? profile.get().nickname()
                    : realName;
        }
        if ("nicked".equals(key))      return String.valueOf(profile.isPresent());
        if ("state".equals(key)) {
            if (!profile.isPresent()) return "none";
            return profile.get().active() ? "active" : "dormant";
        }
        if ("bedwars_level".equals(key)) return resolveLevel(player, profile);
        return null;
    }

    private String resolveLevel(OfflinePlayer player, Optional<DisguiseProfile> profile) {
        if (this.bedwars.isEnabled() && profile.isPresent() && profile.get().active()) {
            return String.valueOf(profile.get().stars());
        }
        String real = this.bedwars.realLevelPlaceholder();
        if (real == null || real.trim().isEmpty()
                || real.toLowerCase(Locale.ROOT).contains("%nick_")) {
            return "0";
        }
        return PlaceholderAPI.setPlaceholders(player, real);
    }
}
""")


# =========================================================================== #
#  8) StorageManager.java
# =========================================================================== #
print("\n[8/9] Rewriting StorageManager.java ...")
write("src/main/java/com/yourname/nick/storage/StorageManager.java", r"""package com.yourname.nick.storage;

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
 *
 * NOTE: The Rank concept was removed from the plugin, but the "rank_used"
 * column is kept in the schema so that existing databases do not break.
 * New rows write the literal string "NONE" into that column and the value
 * is never read back.
 *
 * Never calls Connection#isValid(int): the driver bundled with Spigot
 * 1.8.8 does not implement it and Java 17 throws AbstractMethodError.
 */
public final class StorageManager {

    private static final String COLUMNS =
            "real_uuid, real_name, nickname, rank_used, skin_source, skin_value, "
            + "skin_signature, action, created_at, ip";

    private static final String RANK_PLACEHOLDER = "NONE";

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
                    ps.setString(4,  RANK_PLACEHOLDER);   // rank_used — legacy column
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
                    + "rank_used VARCHAR(16) NOT NULL,"   // legacy, kept for compat
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
                    + "rank_used TEXT NOT NULL,"           // legacy, kept for compat
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

    /** Reads a row. The rank_used column is intentionally ignored. */
    private static NickRecord map(ResultSet rs) throws SQLException {
        return new NickRecord(
                UUID.fromString(rs.getString("real_uuid")),
                rs.getString("real_name"),
                rs.getString("nickname"),
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
""")


# =========================================================================== #
#  9) gui.yml  +  targeted patches
# =========================================================================== #
print("\n[9/9] Updating gui.yml and MineStormNickPlugin.java ...")

write("src/main/resources/gui.yml", r"""# -----------------------------------------------------------------------------
# gui.yml - strings shown inside the /nick setup book.
# Hot-reloadable with /minestormnicksystem reload.
#
# NOTE: The Rank page has been removed. Setup flow is now:
#   Start -> Skin -> Name -> (Roller) -> Done
# -----------------------------------------------------------------------------

book:
  title:  "Nickname Setup"
  author: "MineStormNickSystem"

skin:
  title: ""
  body:
    - "&0Let's get you set up with your nickname!"
    - "&0First, choose which &lSKIN&r&0 you'd like to wear while nicked."
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
    - "&0Alright, now choose the &lNAME&r&0 you want to use!"
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
    - "&0You are now nicked as &7%name%&0."
    - ""
    - "&0To go back to being your usual self, type:"
    - "&c/nick reset"

buttons:
  start:
    label: "&a[ Start setup ]"
    command: "/nick ui skin"
    hover: "Begin the setup"
""")


# Targeted patch: fix the misleading version message in MineStormNickPlugin
patch(
    "src/main/java/com/yourname/nick/MineStormNickPlugin.java",
    '"MineStormNickSystem requires Paper 1.19.3 or newer (player info update packets). Disabling."',
    '"MineStormNickSystem requires Spigot/Paper 1.8.8 (NMS v1_8_R3). Disabling."',
)


print("\n============================================================")
print(" Done.")
print("============================================================")
print(" Removed : Rank.java (and every reference to the rank system)")
print(" Updated : model/DisguiseProfile.java")
print(" Updated : model/NickRecord.java")
print(" Updated : gui/NickSession.java")
print(" Updated : gui/BookGUIManager.java  (no more rank picker)")
print(" Updated : disguise/DisguiseManager.java")
print(" Updated : integration/NickPlaceholderExpansion.java")
print(" Updated : storage/StorageManager.java  (legacy-safe schema)")
print(" Updated : resources/gui.yml")
print(" Patched : MineStormNickPlugin.java (version message)")
print()
print(" World restrictions: WorldRules already returns true everywhere,")
print(" so nicknames take effect instantly in any world.")
print()
print(" Next step:  mvn -B clean package")
print("============================================================")