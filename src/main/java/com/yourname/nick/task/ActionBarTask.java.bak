package com.yourname.nick.task;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import net.md_5.bungee.api.ChatMessageType;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

/**
 * Sends the "you are nicked" indicator through the action bar, never
 * through chat. Only players with an active (or, when configured, a
 * dormant) disguise receive the message.
 *
 * <p>Bug fixed: the previous implementation called
 * {@link Player#sendMessage(String)} every scheduler tick which spammed
 * the public chat with "You are currently NICKED" and got compounded on
 * every plugin reload (which is where the "(3)" suffix came from).</p>
 */
public final class ActionBarTask implements Runnable {

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;
    private final String indicator;
    private final boolean showWhenDormant;

    public ActionBarTask(NickPlugin plugin,
                         DisguiseRegistry registry,
                         String indicator,
                         boolean showWhenDormant) {
        this.plugin = plugin;
        this.registry = registry;
        this.indicator = ChatColor.translateAlternateColorCodes(
                '&', indicator == null ? "" : indicator);
        this.showWhenDormant = showWhenDormant;
    }

    @Override
    public void run() {
        if (this.indicator.isEmpty()) {
            return;
        }
        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player == null || !player.isOnline()) {
                continue;
            }
            if (!profile.active() && !this.showWhenDormant) {
                continue;
            }
            try {
                player.spigot().sendMessage(
                        ChatMessageType.ACTION_BAR,
                        TextComponent.fromLegacyText(this.indicator));
            } catch (Throwable ignored) {
                // One bad player connection must never kill the task.
            }
        }
    }
}
