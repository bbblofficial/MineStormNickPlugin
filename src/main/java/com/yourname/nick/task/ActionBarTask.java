package com.yourname.nick.task;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Method;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

public final class ActionBarTask implements Runnable {

    /** null == Spigot 1.8.8 fallback (BaseComponent[]). */
    private static final Method ACTIONBAR_METHOD = resolve();
    private static final Object ACTIONBAR_ENUM_VALUE = resolveEnum();

    private static Method resolve() {
        try {
            Class<?> spigot = Class.forName("org.bukkit.entity.Player$Spigot");
            Class<?> type   = Class.forName("net.md_5.bungee.api.ChatMessageType");
            return spigot.getMethod("sendMessage", type, BaseComponent[].class);
        } catch (Throwable ignored) { return null; }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static Object resolveEnum() {
        try {
            Class<?> type = Class.forName("net.md_5.bungee.api.ChatMessageType");
            return Enum.valueOf((Class<? extends Enum>) type, "ACTION_BAR");
        } catch (Throwable ignored) { return null; }
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
                if (ACTIONBAR_METHOD != null && ACTIONBAR_ENUM_VALUE != null) {
                    ACTIONBAR_METHOD.invoke(player.spigot(),
                            ACTIONBAR_ENUM_VALUE, components);
                } else {
                    player.spigot().sendMessage(components);
                }
            } catch (Throwable ignored) { }
        }
    }
}
