package com.yourname.nick.command;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseManager;
import com.yourname.nick.gui.BookGUIManager;
import com.yourname.nick.message.Messages;
import com.yourname.nick.model.SkinData;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.skin.SkinCacheManager;
import com.yourname.nick.util.Async;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiConsumer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;

public final class NickCommand implements TabExecutor {

    private final NickPlugin plugin;
    private final Messages messages;
    private final BookGUIManager bookGui;
    private final DisguiseManager disguises;
    private final SkinCacheManager skins;
    private final NameValidator validator;

    public NickCommand(NickPlugin plugin,
                       Messages messages,
                       BookGUIManager bookGui,
                       DisguiseManager disguises,
                       SkinCacheManager skins,
                       NameValidator validator) {
        this.plugin = plugin;
        this.messages = messages;
        this.bookGui = bookGui;
        this.disguises = disguises;
        this.skins = skins;
        this.validator = validator;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage(this.messages.get("player-only"));
            return true;
        }
        Player player = (Player) sender;
        if (args.length == 0) {
            this.bookGui.open(player);
            return true;
        }
        String sub = args[0].toLowerCase(Locale.ROOT);
        if ("reset".equals(sub)) {
            handleReset(player);
        } else if ("skin".equals(sub)) {
            handleSkin(player, args);
        } else if ("name".equals(sub)) {
            handleName(player, args);
        } else if ("ui".equals(sub)) {
            this.bookGui.handle(player, Arrays.copyOfRange(args, 1, args.length));
        } else {
            player.sendMessage(this.messages.get("usage"));
        }
        return true;
    }

    private void handleReset(Player player) {
        this.bookGui.clearSession(player.getUniqueId());
        if (this.disguises.reset(player)) {
            player.sendMessage(this.messages.get("nick-reset"));
        } else {
            player.sendMessage(this.messages.get("nick-not-nicked"));
        }
    }

    private void handleSkin(final Player player, String[] args) {
        if (!player.hasPermission("nick.skin")) {
            player.sendMessage(this.messages.get("no-permission"));
            return;
        }
        if (args.length < 2) {
            player.sendMessage(this.messages.get("skin-usage"));
            return;
        }
        final String target = args[1];
        if (!NameValidator.isValidFormat(target)) {
            player.sendMessage(this.messages.get("skin-invalid-name"));
            return;
        }
        if (!this.disguises.profile(player.getUniqueId()).isPresent()) {
            player.sendMessage(this.messages.get("skin-needs-nick"));
            return;
        }
        player.sendMessage(this.messages.get("skin-fetching", "player", target));

        CompletableFuture<Optional<SkinData>> future = this.skins.fetchByName(target);
        future.whenComplete(new BiConsumer<Optional<SkinData>, Throwable>() {
            @Override
            public void accept(final Optional<SkinData> result, final Throwable error) {
                Async.main(NickCommand.this.plugin, new Runnable() {
                    @Override
                    public void run() {
                        if (!player.isOnline()) {
                            return;
                        }
                        if (error != null) {
                            player.sendMessage(messages.get("skin-fetch-failed"));
                            return;
                        }
                        if (!result.isPresent()) {
                            player.sendMessage(messages.get("skin-not-found",
                                    "player", target));
                            return;
                        }
                        if (disguises.changeSkin(player, result.get())) {
                            player.sendMessage(messages.get("skin-applied",
                                    "player", target));
                        } else {
                            player.sendMessage(messages.get("skin-needs-nick"));
                        }
                    }
                });
            }
        });
    }

    private void handleName(Player player, String[] args) {
        if (!player.hasPermission("nick.custom")) {
            player.sendMessage(this.messages.get("no-permission"));
            return;
        }
        if (args.length < 2) {
            player.sendMessage(this.messages.get("name-usage"));
            return;
        }
        this.bookGui.applyCustomName(player, args[1]);
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length != 1) {
            return Collections.emptyList();
        }
        List<String> options = new ArrayList<String>();
        options.add("reset");
        if (sender.hasPermission("nick.skin"))   options.add("skin");
        if (sender.hasPermission("nick.custom")) options.add("name");

        String typed = args[0].toLowerCase(Locale.ROOT);
        List<String> out = new ArrayList<String>();
        for (String option : options) {
            if (option.startsWith(typed)) {
                out.add(option);
            }
        }
        return out;
    }
}
