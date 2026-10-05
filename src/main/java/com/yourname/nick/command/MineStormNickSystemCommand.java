package com.yourname.nick.command;

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
