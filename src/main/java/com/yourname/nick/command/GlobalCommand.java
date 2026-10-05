package com.yourname.nick.command;

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
