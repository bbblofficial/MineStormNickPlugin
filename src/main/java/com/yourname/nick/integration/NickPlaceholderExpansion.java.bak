package com.yourname.nick.integration;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.util.Locale;
import java.util.Optional;
import me.clip.placeholderapi.PlaceholderAPI;
import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.OfflinePlayer;


public final class NickPlaceholderExpansion
  extends PlaceholderExpansion
{
  private final NickPlugin plugin;
  private final DisguiseRegistry registry;
  private final BedwarsLevelHook bedwars;
  
  public NickPlaceholderExpansion(NickPlugin plugin, DisguiseRegistry registry, BedwarsLevelHook bedwars) {
    this.plugin = plugin;
    this.registry = registry;
    this.bedwars = bedwars;
  }
  public String getIdentifier() {
    return "nick";
  }
  public String getAuthor() {
    return String.join(", ", this.plugin.getDescription().getAuthors());
  }
  public String getVersion() {
    return this.plugin.getDescription().getVersion();
  } public boolean persist() {
    return true;
  }
  
  public String onRequest(OfflinePlayer player, String params) {
    if (player == null) return "";
    
    Optional<DisguiseProfile> profile = this.registry.get(player.getUniqueId());

    
    String realName = profile.isPresent() ? ((DisguiseProfile)profile.get()).realName() : ((player.getName() == null) ? "" : player.getName());
    
    String key = (params == null) ? "" : params.toLowerCase(Locale.ROOT);
    if ("realname".equals(key)) return realName; 
    if ("nick".equals(key)) return profile.isPresent() ? ((DisguiseProfile)profile.get()).nickname() : ""; 
    if ("displayname".equals(key)) {
      return (profile.isPresent() && ((DisguiseProfile)profile.get()).active()) ? (
        (DisguiseProfile)profile.get()).nickname() : 
        realName;
    }
    if ("nicked".equals(key)) return String.valueOf(profile.isPresent()); 
    if ("state".equals(key)) {
      if (!profile.isPresent()) return "none"; 
      return ((DisguiseProfile)profile.get()).active() ? "active" : "dormant";
    } 
    if ("rank".equals(key)) return profile.isPresent() ? ((DisguiseProfile)profile.get()).rank().label() : ""; 
    if ("bedwars_level".equals(key)) return resolveLevel(player, profile); 
    return null;
  }
  
  private String resolveLevel(OfflinePlayer player, Optional<DisguiseProfile> profile) {
    if (this.bedwars.isEnabled() && profile.isPresent() && ((DisguiseProfile)profile.get()).active()) {
      return String.valueOf(((DisguiseProfile)profile.get()).stars());
    }
    String real = this.bedwars.realLevelPlaceholder();
    if (real == null || real.trim().isEmpty() || real
      .toLowerCase(Locale.ROOT).contains("%nick_")) {
      return "0";
    }
    return PlaceholderAPI.setPlaceholders(player, real);
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\integration\NickPlaceholderExpansion.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */