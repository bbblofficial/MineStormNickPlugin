package com.yourname.nick.disguise;

import java.util.logging.Logger;
import org.bukkit.configuration.ConfigurationSection;

/**
 * World restrictions were removed. Nicknames are now active everywhere
 * the moment they are applied, matching Hypixel's behaviour.
 * Kept as a class so existing callers still compile.
 */
public final class WorldRules {

    private static final WorldRules INSTANCE = new WorldRules();

    private WorldRules() {
    }

    public static WorldRules fromConfig(ConfigurationSection config, Logger logger) {
        // worlds.* is intentionally ignored now.
        return INSTANCE;
    }

    public boolean isActive(String worldName) {
        return true;
    }
}
