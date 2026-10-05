package com.yourname.nick.gui;

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
