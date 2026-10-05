#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py
========
Applies the complete "Hypixel-style" nickname behaviour to NickSystem:

  1. Nickname is active everywhere (no more in-game-only / world whitelist).
  2. Action bar message no longer says "(in games only)".
  3. The whole /nick setup flow runs inside a written book (Book GUI),
     with clickable / hoverable text and zero chat-based prompts.
  4. VirtualBook now supports rich BaseComponents (click + hover events).
  5. config.yml's "worlds:" block is neutralised.

Place this file next to the extracted source root (the folder that contains
`com/`, `config.yml`, `messages.yml`, `plugin.yml`, `names.yml`) and run:

    python fixer.py
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
#  Utilities
# ---------------------------------------------------------------------------

def _strip_decompiler(content: str) -> str:
    """Remove the /*  123  */  prefixes that jd-gui inserts."""
    out = []
    for line in content.split("\n"):
        m = re.match(r"^\s*/\*\s*\d*\s*\*/\s?(.*)$", line)
        out.append(m.group(1) if m else line)
    return "\n".join(out)


def write_file(rel_path: str, content: str) -> None:
    full = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    print("[fixer] wrote   " + rel_path)


def patch_file(rel_path: str, patcher) -> None:
    full = os.path.join(ROOT, rel_path)
    if not os.path.isfile(full):
        print("[fixer] SKIP (not found): " + rel_path)
        return
    with open(full, "r", encoding="utf-8") as fh:
        content = _strip_decompiler(fh.read())
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(patcher(content))
    print("[fixer] patched " + rel_path)


# ---------------------------------------------------------------------------
#  1. WorldRules.java  -- always active
# ---------------------------------------------------------------------------

WORLDRULES_JAVA = r'''package com.yourname.nick.disguise;

import java.util.logging.Logger;
import org.bukkit.configuration.ConfigurationSection;

/**
 * World restrictions have been removed. Nicknames are now applied
 * instantly and everywhere, matching the Hypixel Nick behaviour.
 * The class is kept so existing callers keep compiling.
 */
public final class WorldRules {

    private static final WorldRules INSTANCE = new WorldRules();

    private WorldRules() {
    }

    public static WorldRules fromConfig(ConfigurationSection config, Logger logger) {
        // The worlds.* section is intentionally ignored now.
        return INSTANCE;
    }

    public boolean isActive(String worldName) {
        return true;
    }
}
'''


# ---------------------------------------------------------------------------
#  2. VirtualBook.java  -- rich BaseComponent pages
# ---------------------------------------------------------------------------

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

/**
 * Builds and opens written books. Supports both legacy string pages and
 * rich BaseComponent pages (with click / hover events) which is what the
 * Hypixel-style nick GUI relies on.
 */
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
     * Builds a book whose pages are rich chat components. Uses
     * {@code BookMeta.Spigot#setPages} if available so click / hover
     * events work on 1.8.8, otherwise falls back to legacy strings.
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
            // Fall back to legacy below.
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

    /** Opens the given book for the player via the 1.8 NMS book packet. */
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


# ---------------------------------------------------------------------------
#  3. BookGUIManager.java  -- book-only flow
# ---------------------------------------------------------------------------

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
 * Entirely book-driven nickname setup. All navigation happens through
 * clickable text inside a written book -- no chat prompts are ever sent
 * for the UI, matching the Hypixel Nick flow.
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
        this.plugin     = plugin;
        this.messages   = messages;
        this.disguises  = disguises;
        this.skins      = skins;
        this.generator  = generator;
        this.validator  = validator;
        this.storage    = storage;
    }

    /* -------------------------------------------------------------- */
    /*  Entry points                                                  */
    /* -------------------------------------------------------------- */

    public void open(final Player player) {
        this.storage.findLastSetForPlayer(player.getUniqueId()).whenComplete(
                new BiConsumer<Optional<NickRecord>, Throwable>() {
                    @Override
                    public void accept(final Optional<NickRecord> last,
                                       final Throwable error) {
                        Async.main(BookGUIManager.this.plugin, new Runnable() {
                            @Override
                            public void run() {
                                if (!player.isOnline()) {
                                    return;
                                }
                                NickRecord history =
                                        (error == null && last != null && last.isPresent())
                                                ? last.get() : null;
                                NickSession session = new NickSession(history);
                                BookGUIManager.this.sessions.put(
                                        player.getUniqueId(), session);
                                BookGUIManager.this.showIntro(player);
                            }
                        });
                    }
                });
    }

    public void handle(Player player, String[] args) {
        NickSession session = this.sessions.get(player.getUniqueId());
        if (session == null) {
            // No active session -> silently restart the whole flow in the book.
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
        else if ("close".equals(sub))    { /* player will close the book */ }
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
            // Reopen the name picker in the book. No chat error message.
            showName(player, session != null ? session : new NickSession(null));
            return;
        }

        this.disguises.apply(player, nick, rank, skin);
        this.sessions.remove(player.getUniqueId());
        showFinished(player, nick);
    }

    public void clearSession(UUID uuid) { this.sessions.remove(uuid); }

    public void clear()                 { this.sessions.clear(); }

    /* -------------------------------------------------------------- */
    /*  Book pages                                                    */
    /* -------------------------------------------------------------- */

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
        out.add(button("[ My normal skin ]", "/nick ui skin normal",
                "Keep your own skin"));
        out.add(button("[ Steve/Alex ]", "/nick ui skin default",
                "Default skin"));
        out.add(button("[ Random skin ]", "/nick ui skin random",
                "Random from the pool"));
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
                button("[ TRY AGAIN ]", "/nick ui reroll",
                        "Generate a different name")
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

    /* -------------------------------------------------------------- */
    /*  Step handlers                                                 */
    /* -------------------------------------------------------------- */

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
            // No free name found -> stay in the book, back to the picker.
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

    /* -------------------------------------------------------------- */
    /*  Component helpers                                             */
    /* -------------------------------------------------------------- */

    private void openBook(Player player, BaseComponent[] page) {
        VirtualBook.open(player,
                VirtualBook.buildComponents(BOOK_TITLE, BOOK_AUTHOR, page));
    }

    private static BaseComponent blank() {
        return new TextComponent("\n");
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


# ---------------------------------------------------------------------------
#  4. ActionBarTask.java  -- drop the "dormant" branch
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
#  5. messages.yml  -- drop "(in games only)"
# ---------------------------------------------------------------------------

def patch_messages(content: str) -> str:
    return re.sub(
        r'actionbar:\s*".*?"',
        'actionbar: "&c&lYou are currently NICKED"',
        content,
        count=1,
    )


# ---------------------------------------------------------------------------
#  6. config.yml  -- comment out the worlds block
# ---------------------------------------------------------------------------

def patch_config(content: str) -> str:
    lines = content.split("\n")
    out = []
    in_worlds = False
    for line in lines:
        if line.startswith("worlds:"):
            in_worlds = True
            out.append("# World restrictions are no longer used - nicks are")
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
    return "\n".join(out)


# ---------------------------------------------------------------------------
#  Driver
# ---------------------------------------------------------------------------

def main() -> None:
    write_file("com/yourname/nick/disguise/WorldRules.java",  WORLDRULES_JAVA)
    write_file("com/yourname/nick/util/VirtualBook.java",     VIRTUALBOOK_JAVA)
    write_file("com/yourname/nick/gui/BookGUIManager.java",   BOOKGUI_JAVA)
    write_file("com/yourname/nick/task/ActionBarTask.java",   ACTIONBAR_JAVA)

    patch_file("messages.yml", patch_messages)
    patch_file("config.yml",   patch_config)

    print("\n[fixer] Done. All changes applied successfully.")
    print("[fixer] Rebuild with: mvn -q clean package")


if __name__ == "__main__":
    main()