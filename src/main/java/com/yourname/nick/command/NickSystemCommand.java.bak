package com.yourname.nick.command;

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
