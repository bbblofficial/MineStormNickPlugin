package com.yourname.nick.task;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Method;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

/**
 * Sends the "you are nicked" indicator through the ACTION BAR only,
 * never through chat.
 *
 * <p>Bug fixes preserved here:</p>
 * <ul>
 *   <li>Chat spam eliminated - the indicator never touches chat.</li>
 *   <li>Version compatibility - Spigot 1.8.8 only ships
 *       {@code Player.Spigot#sendMessage(BaseComponent...)}; the
 *       {@code ChatMessageType} overload came later. We probe for the
 *       newer API once and fall back to the 1.8.8 method.</li>
 * </ul>
 */
public final class ActionBarTask implements Runnable {

    /** Cached at class-load; null means the 1.8.8 method is used. */
    private static final Method ACTIONBAR_METHOD = resolveActionBarMethod();

    private static Method resolveActionBarMethod() {
        try {
            Class<?> spigot = Class.forName("org.bukkit.entity.Player$Spigot");
            Class<?> type   = Class.forName("net.md_5.bungee.api.ChatMessageType");
            return spigot.getMethod("sendMessage", type, BaseComponent[].class);
        } catch (Throwable ignored) {
            return null;
        }
    }

    private final MineStormNickPlugin plugin;
    private final DisguiseRegistry registry;
    private final String indicator;
    private final boolean showWhenDormant;

    public ActionBarTask(MineStormNickPlugin plugin,
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
        if (this.indicator.isEmpty()) return;

        BaseComponent[] components = TextComponent.fromLegacyText(this.indicator);

        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player == null || !player.isOnline()) continue;
            if (!profile.active() && !this.showWhenDormant) continue;

            try {
                if (ACTIONBAR_METHOD != null) {
                    // Paper / newer Spigot: real action-bar slot.
                    Object typeEnum = Enum.valueOf(
                            (Class<? extends Enum>) Class.forName(
                                    "net.md_5.bungee.api.ChatMessageType"),
                            "ACTION_BAR");
                    ACTIONBAR_METHOD.invoke(player.spigot(), typeEnum, components);
                } else {
                    // Spigot 1.8.8: send raw BaseComponent[] (goes to the
                    // action-bar slot on 1.8.8 clients because of how
                    // CraftBukkit patches Spigot#sendMessage).
                    player.spigot().sendMessage(components);
                }
            } catch (Throwable ignored) {
                // One bad connection must never kill the task.
            }
        }
    }
}
