package com.yourname.nick.task;

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
