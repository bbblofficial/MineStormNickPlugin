/*    */ package com.yourname.nick.integration;
/*    */ 
/*    */ import com.yourname.nick.model.DisguiseProfile;
/*    */ import java.util.concurrent.ThreadLocalRandom;
/*    */ import org.bukkit.ChatColor;
/*    */ import org.bukkit.configuration.ConfigurationSection;
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class BedwarsLevelHook
/*    */ {
/*    */   private final boolean enabled;
/*    */   private final int minStars;
/*    */   private final int maxStars;
/*    */   private final boolean chatPrefix;
/*    */   private final String realLevelPlaceholder;
/*    */   
/*    */   public BedwarsLevelHook(ConfigurationSection config) {
/* 22 */     this.enabled = config.getBoolean("integrations.bedwars.enabled", false);
/* 23 */     int min = Math.max(0, config.getInt("integrations.bedwars.min-stars", 1));
/* 24 */     int max = Math.max(min, config.getInt("integrations.bedwars.max-stars", 12));
/* 25 */     this.minStars = min;
/* 26 */     this.maxStars = max;
/* 27 */     this.chatPrefix = config.getBoolean("integrations.bedwars.chat-prefix", true);
/* 28 */     this.realLevelPlaceholder = config.getString("integrations.bedwars.real-level-placeholder", "");
/*    */   }
/*    */   public boolean isEnabled() {
/* 31 */     return this.enabled;
/*    */   }
/*    */   public int rollStars() {
/* 34 */     if (!this.enabled) return 0; 
/* 35 */     return ThreadLocalRandom.current().nextInt(this.minStars, this.maxStars + 1);
/*    */   }
/*    */   
/*    */   public String realLevelPlaceholder() {
/* 39 */     return (this.realLevelPlaceholder == null) ? "" : this.realLevelPlaceholder;
/*    */   }
/*    */ 
/*    */   
/*    */   public String chatPrefix(DisguiseProfile profile) {
/* 44 */     if (!this.enabled || !this.chatPrefix) return null; 
/* 45 */     return ChatColor.GRAY + "[" + profile.stars() + "✫] ";
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\integration\BedwarsLevelHook.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */