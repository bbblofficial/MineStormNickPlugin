package com.yourname.nick.disguise;

import java.util.logging.Logger;
import org.bukkit.configuration.ConfigurationSection;

/**
 * World restrictions removed. Nicknames are active everywhere the moment
 * they are applied.
 */
public final class WorldRules {

    private static final WorldRules INSTANCE = new WorldRules();

    private WorldRules() { }

    public static WorldRules fromConfig(ConfigurationSection config, Logger logger) {
        return INSTANCE;
    }

    public boolean isActive(String worldName) {
        return true;
    }
}
