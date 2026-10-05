/*     */ package com.yourname.nick;
/*     */ 
/*     */ import com.yourname.nick.command.NickCommand;
/*     */ import com.yourname.nick.command.RealNameCommand;
/*     */ import com.yourname.nick.disguise.DisguiseManager;
/*     */ import com.yourname.nick.disguise.DisguiseRegistry;
/*     */ import com.yourname.nick.disguise.WorldRules;
/*     */ import com.yourname.nick.gui.BookGUIManager;
/*     */ import com.yourname.nick.integration.BedwarsLevelHook;
/*     */ import com.yourname.nick.integration.NickPlaceholderExpansion;
/*     */ import com.yourname.nick.listener.ChatListener;
/*     */ import com.yourname.nick.listener.ConnectionListener;
/*     */ import com.yourname.nick.listener.WorldListener;
/*     */ import com.yourname.nick.message.Messages;
/*     */ import com.yourname.nick.name.NameGenerator;
/*     */ import com.yourname.nick.name.NameValidator;
/*     */ import com.yourname.nick.packet.PacketManager;
/*     */ import com.yourname.nick.skin.SkinCacheManager;
/*     */ import com.yourname.nick.storage.StorageManager;
/*     */ import com.yourname.nick.task.ActionBarTask;
/*     */ import com.yourname.nick.util.Async;
/*     */ import java.io.File;
/*     */ import java.util.Objects;
/*     */ import java.util.logging.Level;
/*     */ import org.bukkit.command.CommandExecutor;
/*     */ import org.bukkit.command.PluginCommand;
/*     */ import org.bukkit.command.TabCompleter;
/*     */ import org.bukkit.command.TabExecutor;
/*     */ import org.bukkit.configuration.ConfigurationSection;
/*     */ import org.bukkit.configuration.file.YamlConfiguration;
/*     */ import org.bukkit.event.Listener;
/*     */ import org.bukkit.plugin.Plugin;
/*     */ import org.bukkit.plugin.PluginManager;
/*     */ import org.bukkit.plugin.java.JavaPlugin;
/*     */ 
/*     */ public final class NickPlugin
/*     */   extends JavaPlugin {
/*     */   private DisguiseRegistry registry;
/*     */   private PacketManager packets;
/*     */   private StorageManager storage;
/*     */   
/*     */   public void onLoad() {
/*  43 */     this.registry = new DisguiseRegistry();
/*  44 */     this.packets = new PacketManager(this, this.registry);
/*  45 */     this.packets.load();
/*     */   }
/*     */   private SkinCacheManager skins; private DisguiseManager disguises; private BookGUIManager bookGui; private Runnable placeholderCleanup;
/*     */   
/*     */   public void onEnable() {
/*  50 */     saveDefaultConfig();
/*  51 */     YamlConfiguration names = loadNames();
/*  52 */     Messages messages = new Messages(this);
/*     */     
/*  54 */     if (!this.packets.enable()) {
/*  55 */       getLogger().severe("NickSystem requires Paper 1.19.3 or newer (player info update packets). Disabling.");
/*  56 */       getServer().getPluginManager().disablePlugin((Plugin)this);
/*     */       
/*     */       return;
/*     */     } 
/*  60 */     this.storage = new StorageManager(this);
/*  61 */     this.storage.initialize().whenComplete((ignored, error) -> {
/*     */           if (error != null) {
/*     */             getLogger().log(Level.SEVERE, "Database initialisation failed; disabling NickSystem.", error);
/*     */             
/*     */             Async.main((Plugin)this, ());
/*     */           } 
/*     */         });
/*  68 */     this.skins = new SkinCacheManager(this);
/*  69 */     this.skins.initialize();
/*     */     
/*  71 */     NameValidator validator = new NameValidator(names, this.registry);
/*  72 */     NameGenerator generator = new NameGenerator(names, validator);
/*  73 */     BedwarsLevelHook bedwars = new BedwarsLevelHook((ConfigurationSection)getConfig());
/*  74 */     WorldRules rules = WorldRules.fromConfig((ConfigurationSection)getConfig(), getLogger());
/*     */     
/*  76 */     this.disguises = new DisguiseManager(this, this.registry, this.packets, this.storage, rules, bedwars);
/*  77 */     this.bookGui = new BookGUIManager(this, messages, this.disguises, this.skins, generator, validator, this.storage);
/*     */     
/*  79 */     PluginManager pluginManager = getServer().getPluginManager();
/*  80 */     pluginManager.registerEvents((Listener)new ConnectionListener(this, this.registry, this.disguises, this.storage, this.bookGui), (Plugin)this);
/*  81 */     pluginManager.registerEvents((Listener)new WorldListener(this.disguises), (Plugin)this);
/*  82 */     pluginManager.registerEvents((Listener)new ChatListener((ConfigurationSection)getConfig(), this.registry, bedwars), (Plugin)this);
/*     */     
/*  84 */     bind("nick", (TabExecutor)new NickCommand(this, messages, this.bookGui, this.disguises, this.skins, validator));
/*  85 */     bind("realname", (TabExecutor)new RealNameCommand(this, messages, this.registry, this.storage));
/*     */     
/*  87 */     if (getConfig().getBoolean("actionbar.enabled", true)) {
/*  88 */       long interval = Math.max(10L, getConfig().getLong("actionbar.interval-ticks", 40L));
/*     */       
/*  90 */       ActionBarTask task = new ActionBarTask(this, this.registry, messages.get("actionbar", new String[0]), getConfig().getBoolean("actionbar.show-when-dormant", true));
/*  91 */       getServer().getScheduler().runTaskTimer((Plugin)this, (Runnable)task, interval, interval);
/*     */     } 
/*  93 */     getServer().getScheduler().runTaskTimerAsynchronously((Plugin)this, () -> this.registry.prunePending(60000L), 1200L, 1200L);
/*     */     
/*  95 */     if (pluginManager.isPluginEnabled("PlaceholderAPI")) {
/*  96 */       NickPlaceholderExpansion expansion = new NickPlaceholderExpansion(this, this.registry, bedwars);
/*  97 */       expansion.register();
/*  98 */       Objects.requireNonNull(expansion); this.placeholderCleanup = expansion::unregister;
/*     */     } 
/*     */   }
/*     */ 
/*     */   
/*     */   public void onDisable() {
/* 104 */     getServer().getScheduler().cancelTasks((Plugin)this);
/* 105 */     if (this.placeholderCleanup != null) {
/* 106 */       this.placeholderCleanup.run();
/* 107 */       this.placeholderCleanup = null;
/*     */     } 
/* 109 */     if (this.disguises != null) {
/* 110 */       this.disguises.shutdown();
/*     */     }
/* 112 */     if (this.bookGui != null) {
/* 113 */       this.bookGui.clear();
/*     */     }
/* 115 */     if (this.skins != null) {
/* 116 */       this.skins.shutdown();
/*     */     }
/* 118 */     if (this.storage != null) {
/* 119 */       this.storage.close();
/*     */     }
/* 121 */     if (this.packets != null) {
/* 122 */       this.packets.disable();
/*     */     }
/*     */   }
/*     */   
/*     */   private YamlConfiguration loadNames() {
/* 127 */     File file = new File(getDataFolder(), "names.yml");
/* 128 */     if (!file.exists()) {
/* 129 */       saveResource("names.yml", false);
/*     */     }
/* 131 */     return YamlConfiguration.loadConfiguration(file);
/*     */   }
/*     */   
/*     */   private void bind(String name, TabExecutor executor) {
/* 135 */     PluginCommand command = getCommand(name);
/* 136 */     if (command == null) {
/* 137 */       throw new IllegalStateException("Command '" + name + "' is missing from plugin.yml");
/*     */     }
/* 139 */     command.setExecutor((CommandExecutor)executor);
/* 140 */     command.setTabCompleter((TabCompleter)executor);
/*     */   }
/*     */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\NickPlugin.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */