package com.yourname.nick.integration;

import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

public final class LuckPermsHook {

    private final JavaPlugin plugin;
    private volatile boolean enabled;
    private volatile boolean checkInheritance;
    private volatile String requiredGroup;
    private volatile String fallbackPermission;
    private final Set<String> trackedGroups = new HashSet<String>();

    public LuckPermsHook(JavaPlugin plugin) {
        this.plugin = plugin;
        reload(plugin.getConfig());
    }

    public void reload(FileConfiguration cfg) {
        this.enabled = cfg.getBoolean("luckperms.enabled", true);
        this.requiredGroup = String.valueOf(
                cfg.getString("luckperms.required-group", "prime"))
                .toLowerCase(Locale.ROOT);
        this.checkInheritance = cfg.getBoolean("luckperms.check-inheritance", true);
        this.fallbackPermission = cfg.getString(
                "luckperms.required-permission", "minestormnicksystem.global");
        this.trackedGroups.clear();
        for (String g : cfg.getStringList("luckperms.tracked-groups")) {
            if (g != null && !g.trim().isEmpty()) {
                this.trackedGroups.add(g.toLowerCase(Locale.ROOT));
            }
        }
        if (this.trackedGroups.isEmpty()) this.trackedGroups.add(this.requiredGroup);
    }

    public boolean isRanked(Player player) {
        if (player == null) return false;
        if (this.enabled && hasLuckPerms()) {
            try { if (checkViaLuckPerms(player)) return true; }
            catch (Throwable t) {
                this.plugin.getLogger().fine(
                        "LuckPerms lookup failed, falling back: " + t);
            }
        }
        for (String g : this.trackedGroups) {
            if (player.hasPermission("group." + g)) return true;
        }
        return player.hasPermission(this.fallbackPermission);
    }

    private boolean hasLuckPerms() {
        try {
            Class.forName("net.luckperms.api.LuckPermsProvider");
            return this.plugin.getServer().getPluginManager().isPluginEnabled("LuckPerms");
        } catch (Throwable t) { return false; }
    }

    private boolean checkViaLuckPerms(Player player) throws Exception {
        Class<?> provider = Class.forName("net.luckperms.api.LuckPermsProvider");
        Object luckPerms  = provider.getMethod("get").invoke(null);
        Object userMgr    = luckPerms.getClass().getMethod("getUserManager").invoke(luckPerms);
        Object user = userMgr.getClass().getMethod("getUser", UUID.class)
                .invoke(userMgr, player.getUniqueId());
        if (user == null) return false;
        Object cached = user.getClass().getMethod("getCachedData").invoke(user);
        Object meta   = cached.getClass().getMethod("getMetaData").invoke(cached);
        String primaryGroup = String.valueOf(
                meta.getClass().getMethod("getPrimaryGroup").invoke(meta))
                .toLowerCase(Locale.ROOT);

        if (this.trackedGroups.contains(primaryGroup)) return true;
        if (!this.checkInheritance) return false;

        try {
            Method getInherited = meta.getClass().getMethod("getInheritedGroups");
            Object inherited = getInherited.invoke(meta);
            if (inherited instanceof Iterable) {
                for (Object g : (Iterable<?>) inherited) {
                    String n = String.valueOf(g).toLowerCase(Locale.ROOT);
                    if (this.trackedGroups.contains(n)) return true;
                }
            }
        } catch (NoSuchMethodException ignored) {
            for (String tracked : this.trackedGroups) {
                if (primaryGroup.contains(tracked)) return true;
            }
        }
        return false;
    }

    public String requiredGroup() { return this.requiredGroup; }
}
