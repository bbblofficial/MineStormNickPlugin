package com.yourname.nick.integration;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.util.Locale;
import java.util.Optional;
import me.clip.placeholderapi.PlaceholderAPI;
import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.OfflinePlayer;

public final class NickPlaceholderExpansion extends PlaceholderExpansion {

    private final MineStormNickPlugin plugin;
    private final DisguiseRegistry registry;
    private final BedwarsLevelHook bedwars;

    public NickPlaceholderExpansion(MineStormNickPlugin plugin,
                                    DisguiseRegistry registry,
                                    BedwarsLevelHook bedwars) {
        this.plugin = plugin;
        this.registry = registry;
        this.bedwars = bedwars;
    }

    @Override public String getIdentifier() { return "nick"; }
    @Override public String getAuthor() {
        return String.join(", ", this.plugin.getDescription().getAuthors());
    }
    @Override public String getVersion() {
        return this.plugin.getDescription().getVersion();
    }
    @Override public boolean persist() { return true; }

    @Override
    public String onRequest(OfflinePlayer player, String params) {
        if (player == null) return "";

        Optional<DisguiseProfile> profile = this.registry.get(player.getUniqueId());
        String realName = profile.isPresent()
                ? profile.get().realName()
                : (player.getName() == null ? "" : player.getName());

        String key = (params == null) ? "" : params.toLowerCase(Locale.ROOT);
        if ("realname".equals(key))    return realName;
        if ("nick".equals(key))        return profile.isPresent() ? profile.get().nickname() : "";
        if ("displayname".equals(key)) {
            return (profile.isPresent() && profile.get().active())
                    ? profile.get().nickname()
                    : realName;
        }
        if ("nicked".equals(key))      return String.valueOf(profile.isPresent());
        if ("state".equals(key)) {
            if (!profile.isPresent()) return "none";
            return profile.get().active() ? "active" : "dormant";
        }
        if ("bedwars_level".equals(key)) return resolveLevel(player, profile);
        return null;
    }

    private String resolveLevel(OfflinePlayer player, Optional<DisguiseProfile> profile) {
        if (this.bedwars.isEnabled() && profile.isPresent() && profile.get().active()) {
            return String.valueOf(profile.get().stars());
        }
        String real = this.bedwars.realLevelPlaceholder();
        if (real == null || real.trim().isEmpty()
                || real.toLowerCase(Locale.ROOT).contains("%nick_")) {
            return "0";
        }
        return PlaceholderAPI.setPlaceholders(player, real);
    }
}
