package com.yourname.nick.gui;

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
 * Book-driven nickname setup. Every step is rendered inside a written
 * book with clickable / hoverable text so the chat is never used for
 * UI navigation (Hypixel-style).
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
        this.plugin = plugin;
        this.messages = messages;
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
                        NickRecord history = (error == null && last != null && last.isPresent())
                                ? last.get() : null;
                        NickSession session = new NickSession(history);
                        sessions.put(player.getUniqueId(), session);
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
        if ("rank".equals(sub))          chooseRank(player, session, args);
        else if ("skin".equals(sub))     chooseSkin(player, session, args);
        else if ("name".equals(sub))     chooseName(player, session, args);
        else if ("use".equals(sub))      useRolledName(player, session);
        else if ("reroll".equals(sub))   reroll(player, session);
        else if ("close".equals(sub))    { /* nothing - book closes */ }
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
        out.add(button("[ My normal skin ]", "/nick ui skin normal", "Keep your own skin"));
        out.add(button("[ Steve/Alex ]",     "/nick ui skin default", "Default skin"));
        out.add(button("[ Random skin ]",    "/nick ui skin random", "Random from pool"));
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
                button("[ TRY AGAIN ]", "/nick ui reroll", "Generate a different name")
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

    private void reroll(Player player, NickSession session) {
        rollName(player, session);
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

    private void openBook(Player player, BaseComponent[] page) {
        VirtualBook.open(player,
                VirtualBook.buildComponents(BOOK_TITLE, BOOK_AUTHOR, page));
    }

    private static BaseComponent blank() {
        return new TextComponent(TextComponent.fromLegacyText("\n"));
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
