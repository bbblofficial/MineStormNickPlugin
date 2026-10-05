/*    */ package com.yourname.nick.message;
/*    */ 
/*    */ import com.yourname.nick.util.Chat;
/*    */ import java.io.File;
/*    */ import java.io.InputStream;
/*    */ import java.io.InputStreamReader;
/*    */ import java.nio.charset.StandardCharsets;
/*    */ import org.bukkit.configuration.Configuration;
/*    */ import org.bukkit.configuration.file.YamlConfiguration;
/*    */ import org.bukkit.plugin.java.JavaPlugin;
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class Messages
/*    */ {
/*    */   private final YamlConfiguration yaml;
/*    */   private final String prefix;
/*    */   
/*    */   public Messages(JavaPlugin plugin) {
/* 20 */     File file = new File(plugin.getDataFolder(), "messages.yml");
/* 21 */     if (!file.exists()) plugin.saveResource("messages.yml", false); 
/* 22 */     YamlConfiguration loaded = YamlConfiguration.loadConfiguration(file);
/* 23 */     InputStream defaults = plugin.getResource("messages.yml");
/* 24 */     if (defaults != null) {
/* 25 */       loaded.setDefaults((Configuration)YamlConfiguration.loadConfiguration(new InputStreamReader(defaults, StandardCharsets.UTF_8)));
/*    */     }
/*    */     
/* 28 */     this.yaml = loaded;
/* 29 */     this.prefix = Chat.color(loaded.getString("prefix", ""));
/*    */   }
/*    */   
/*    */   public String get(String key, String... placeholders) {
/* 33 */     String raw = this.yaml.getString(key);
/* 34 */     if (raw == null) raw = "&cMissing message: " + key; 
/* 35 */     String out = raw;
/* 36 */     for (int i = 0; i + 1 < placeholders.length; i += 2) {
/* 37 */       out = out.replace("%" + placeholders[i] + "%", placeholders[i + 1]);
/*    */     }
/* 39 */     return Chat.color(out);
/*    */   }
/*    */   
/*    */   public String prefixed(String key, String... placeholders) {
/* 43 */     return this.prefix + get(key, placeholders);
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\message\Messages.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */