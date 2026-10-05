/*    */ package com.yourname.nick.integration;
/*    */ 
/*    */ import com.yourname.nick.NickPlugin;
/*    */ import com.yourname.nick.disguise.DisguiseRegistry;
/*    */ import com.yourname.nick.model.DisguiseProfile;
/*    */ import java.util.Locale;
/*    */ import java.util.Optional;
/*    */ import me.clip.placeholderapi.PlaceholderAPI;
/*    */ import me.clip.placeholderapi.expansion.PlaceholderExpansion;
/*    */ import org.bukkit.OfflinePlayer;
/*    */ 
/*    */ 
/*    */ public final class NickPlaceholderExpansion
/*    */   extends PlaceholderExpansion
/*    */ {
/*    */   private final NickPlugin plugin;
/*    */   private final DisguiseRegistry registry;
/*    */   private final BedwarsLevelHook bedwars;
/*    */   
/*    */   public NickPlaceholderExpansion(NickPlugin plugin, DisguiseRegistry registry, BedwarsLevelHook bedwars) {
/* 21 */     this.plugin = plugin;
/* 22 */     this.registry = registry;
/* 23 */     this.bedwars = bedwars;
/*    */   }
/*    */   public String getIdentifier() {
/* 26 */     return "nick";
/*    */   }
/*    */   public String getAuthor() {
/* 29 */     return String.join(", ", this.plugin.getDescription().getAuthors());
/*    */   }
/*    */   public String getVersion() {
/* 32 */     return this.plugin.getDescription().getVersion();
/*    */   } public boolean persist() {
/* 34 */     return true;
/*    */   }
/*    */   
/*    */   public String onRequest(OfflinePlayer player, String params) {
/* 38 */     if (player == null) return "";
/*    */     
/* 40 */     Optional<DisguiseProfile> profile = this.registry.get(player.getUniqueId());
/*    */ 
/*    */     
/* 43 */     String realName = profile.isPresent() ? ((DisguiseProfile)profile.get()).realName() : ((player.getName() == null) ? "" : player.getName());
/*    */     
/* 45 */     String key = (params == null) ? "" : params.toLowerCase(Locale.ROOT);
/* 46 */     if ("realname".equals(key)) return realName; 
/* 47 */     if ("nick".equals(key)) return profile.isPresent() ? ((DisguiseProfile)profile.get()).nickname() : ""; 
/* 48 */     if ("displayname".equals(key)) {
/* 49 */       return (profile.isPresent() && ((DisguiseProfile)profile.get()).active()) ? (
/* 50 */         (DisguiseProfile)profile.get()).nickname() : 
/* 51 */         realName;
/*    */     }
/* 53 */     if ("nicked".equals(key)) return String.valueOf(profile.isPresent()); 
/* 54 */     if ("state".equals(key)) {
/* 55 */       if (!profile.isPresent()) return "none"; 
/* 56 */       return ((DisguiseProfile)profile.get()).active() ? "active" : "dormant";
/*    */     } 
/* 58 */     if ("rank".equals(key)) return profile.isPresent() ? ((DisguiseProfile)profile.get()).rank().label() : ""; 
/* 59 */     if ("bedwars_level".equals(key)) return resolveLevel(player, profile); 
/* 60 */     return null;
/*    */   }
/*    */   
/*    */   private String resolveLevel(OfflinePlayer player, Optional<DisguiseProfile> profile) {
/* 64 */     if (this.bedwars.isEnabled() && profile.isPresent() && ((DisguiseProfile)profile.get()).active()) {
/* 65 */       return String.valueOf(((DisguiseProfile)profile.get()).stars());
/*    */     }
/* 67 */     String real = this.bedwars.realLevelPlaceholder();
/* 68 */     if (real == null || real.trim().isEmpty() || real
/* 69 */       .toLowerCase(Locale.ROOT).contains("%nick_")) {
/* 70 */       return "0";
/*    */     }
/* 72 */     return PlaceholderAPI.setPlaceholders(player, real);
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\integration\NickPlaceholderExpansion.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */