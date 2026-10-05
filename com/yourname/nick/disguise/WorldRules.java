package com.yourname.nick.disguise;

import java.util.logging.Logger;
import org.bukkit.configuration.ConfigurationSection;

/**
 * World restrictions have been removed. Nicknames are now applied
 * instantly and everywhere, matching the Hypixel Nick behaviour.
 * The class is kept so existing callers keep compiling.
 */
public final class WorldRules {

    private static final WorldRules INSTANCE = new WorldRules();

    private WorldRules() {
    }

    public static WorldRules fromConfig(ConfigurationSection config, Logger logger) {
        // The worlds.* section is intentionally ignored now.
        return INSTANCE;
    }

    public boolean isActive(String worldName) {
        return true;
    }
}
