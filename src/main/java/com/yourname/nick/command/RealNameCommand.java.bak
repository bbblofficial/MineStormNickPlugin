package com.yourname.nick.command;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.message.Messages;
import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.storage.StorageManager;
import com.yourname.nick.util.Async;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.function.BiConsumer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;

public final class RealNameCommand implements TabExecutor {

    private static final DateTimeFormatter DATE_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm 'UTC'").withZone(ZoneOffset.UTC);

    private final NickPlugin plugin;
    private final Messages messages;
    private final DisguiseRegistry registry;
    private final StorageManager storage;

    public RealNameCommand(NickPlugin plugin,
                           Messages messages,
                           DisguiseRegistry registry,
                           StorageManager storage) {
        this.plugin = plugin;
        this.messages = messages;
        this.registry = registry;
        this.storage = storage;
    }

    @Override
    public boolean onCommand(final CommandSender sender, Command command, String label, String[] args) {
        if (!sender.hasPermission("nick.staff")) {
            sender.sendMessage(this.messages.get("no-permission"));
            return true;
        }
        if (args.length != 1) {
            sender.sendMessage(this.messages.get("realname-usage"));
            return true;
        }
        final String nick = args[0];
        if (!NameValidator.isValidFormat(nick)) {
            sender.sendMessage(this.messages.get("realname-none", "nick", nick));
            return true;
        }

        Optional<DisguiseProfile> live = this.registry.findByNick(nick);
        if (live.isPresent()) {
            DisguiseProfile profile = live.get();
            sender.sendMessage(this.messages.get("realname-live",
                    "nick",  profile.nickname(),
                    "real",  profile.realName(),
                    "uuid",  profile.realUuid().toString(),
                    "state", profile.active() ? "active" : "dormant"));
            return true;
        }

        this.storage.findLatestByNickname(nick).whenComplete(
                new BiConsumer<Optional<NickRecord>, Throwable>() {
            @Override
            public void accept(final Optional<NickRecord> row, final Throwable error) {
                Async.main(RealNameCommand.this.plugin, new Runnable() {
                    @Override
                    public void run() {
                        if (error != null) {
                            sender.sendMessage(messages.get("storage-error"));
                            return;
                        }
                        if (!row.isPresent()) {
                            sender.sendMessage(messages.get("realname-none", "nick", nick));
                            return;
                        }
                        NickRecord record = row.get();
                        sender.sendMessage(messages.get("realname-historical",
                                "nick", record.nickname(),
                                "real", record.realName(),
                                "uuid", record.realUuid().toString(),
                                "date", DATE_FORMAT.format(
                                        Instant.ofEpochMilli(record.createdAt()))));
                    }
                });
            }
        });
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length != 1 || !sender.hasPermission("nick.staff")) {
            return Collections.emptyList();
        }
        String typed = args[0].toLowerCase(Locale.ROOT);
        List<String> out = new ArrayList<String>();
        for (DisguiseProfile profile : this.registry.all()) {
            String n = profile.nickname();
            if (n != null && n.toLowerCase(Locale.ROOT).startsWith(typed)) {
                out.add(n);
            }
        }
        return out;
    }
}
