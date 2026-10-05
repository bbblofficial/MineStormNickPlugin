/*     */ package com.yourname.nick.command;
/*     */ 
/*     */ import com.yourname.nick.NickPlugin;
/*     */ import com.yourname.nick.disguise.DisguiseManager;
/*     */ import com.yourname.nick.gui.BookGUIManager;
/*     */ import com.yourname.nick.message.Messages;
/*     */ import com.yourname.nick.model.SkinData;
/*     */ import com.yourname.nick.name.NameValidator;
/*     */ import com.yourname.nick.skin.SkinCacheManager;
/*     */ import com.yourname.nick.util.Async;
/*     */ import java.util.ArrayList;
/*     */ import java.util.Arrays;
/*     */ import java.util.Collections;
/*     */ import java.util.List;
/*     */ import java.util.Locale;
/*     */ import java.util.Optional;
/*     */ import java.util.concurrent.CompletableFuture;
/*     */ import java.util.function.BiConsumer;
/*     */ import org.bukkit.command.Command;
/*     */ import org.bukkit.command.CommandSender;
/*     */ import org.bukkit.command.TabExecutor;
/*     */ import org.bukkit.entity.Player;
/*     */ import org.bukkit.plugin.Plugin;
/*     */ 
/*     */ public final class NickCommand
/*     */   implements TabExecutor {
/*     */   private final NickPlugin plugin;
/*     */   private final Messages messages;
/*     */   private final BookGUIManager bookGui;
/*     */   private final DisguiseManager disguises;
/*     */   private final SkinCacheManager skins;
/*     */   private final NameValidator validator;
/*     */   
/*     */   public NickCommand(NickPlugin plugin, Messages messages, BookGUIManager bookGui, DisguiseManager disguises, SkinCacheManager skins, NameValidator validator) {
/*  35 */     this.plugin = plugin;
/*  36 */     this.messages = messages;
/*  37 */     this.bookGui = bookGui;
/*  38 */     this.disguises = disguises;
/*  39 */     this.skins = skins;
/*  40 */     this.validator = validator;
/*     */   }
/*     */ 
/*     */   
/*     */   public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
/*  45 */     if (!(sender instanceof Player)) {
/*  46 */       sender.sendMessage(this.messages.get("player-only", new String[0]));
/*  47 */       return true;
/*     */     } 
/*  49 */     Player player = (Player)sender;
/*  50 */     if (args.length == 0) {
/*  51 */       this.bookGui.open(player);
/*  52 */       return true;
/*     */     } 
/*  54 */     String sub = args[0].toLowerCase(Locale.ROOT);
/*  55 */     if ("reset".equals(sub)) {
/*  56 */       handleReset(player);
/*  57 */     } else if ("skin".equals(sub)) {
/*  58 */       handleSkin(player, args);
/*  59 */     } else if ("name".equals(sub)) {
/*  60 */       handleName(player, args);
/*  61 */     } else if ("ui".equals(sub)) {
/*  62 */       this.bookGui.handle(player, Arrays.<String>copyOfRange(args, 1, args.length));
/*     */     } else {
/*  64 */       player.sendMessage(this.messages.get("usage", new String[0]));
/*     */     } 
/*  66 */     return true;
/*     */   }
/*     */   
/*     */   private void handleReset(Player player) {
/*  70 */     this.bookGui.clearSession(player.getUniqueId());
/*  71 */     if (this.disguises.reset(player)) {
/*  72 */       player.sendMessage(this.messages.get("nick-reset", new String[0]));
/*     */     } else {
/*  74 */       player.sendMessage(this.messages.get("nick-not-nicked", new String[0]));
/*     */     } 
/*     */   }
/*     */   
/*     */   private void handleSkin(final Player player, String[] args) {
/*  79 */     if (!player.hasPermission("nick.skin")) {
/*  80 */       player.sendMessage(this.messages.get("no-permission", new String[0]));
/*     */       return;
/*     */     } 
/*  83 */     if (args.length < 2) {
/*  84 */       player.sendMessage(this.messages.get("skin-usage", new String[0]));
/*     */       return;
/*     */     } 
/*  87 */     final String target = args[1];
/*  88 */     if (!NameValidator.isValidFormat(target)) {
/*  89 */       player.sendMessage(this.messages.get("skin-invalid-name", new String[0]));
/*     */       return;
/*     */     } 
/*  92 */     if (!this.disguises.profile(player.getUniqueId()).isPresent()) {
/*  93 */       player.sendMessage(this.messages.get("skin-needs-nick", new String[0]));
/*     */       return;
/*     */     } 
/*  96 */     player.sendMessage(this.messages.get("skin-fetching", new String[] { "player", target }));
/*     */     
/*  98 */     CompletableFuture<Optional<SkinData>> future = this.skins.fetchByName(target);
/*  99 */     future.whenComplete(new BiConsumer<Optional<SkinData>, Throwable>()
/*     */         {
/*     */           public void accept(final Optional<SkinData> result, final Throwable error) {
/* 102 */             Async.main((Plugin)NickCommand.this.plugin, new Runnable()
/*     */                 {
/*     */                   public void run() {
/* 105 */                     if (!player.isOnline())
/* 106 */                       return;  if (error != null) {
/* 107 */                       player.sendMessage(NickCommand.this.messages.get("skin-fetch-failed", new String[0]));
/*     */                       return;
/*     */                     } 
/* 110 */                     if (!result.isPresent()) {
/* 111 */                       player.sendMessage(NickCommand.this.messages.get("skin-not-found", new String[] { "player", this.this$1.val$target }));
/*     */                       return;
/*     */                     } 
/* 114 */                     if (NickCommand.this.disguises.changeSkin(player, result.get())) {
/* 115 */                       player.sendMessage(NickCommand.this.messages.get("skin-applied", new String[] { "player", this.this$1.val$target }));
/*     */                     } else {
/* 117 */                       player.sendMessage(NickCommand.this.messages.get("skin-needs-nick", new String[0]));
/*     */                     } 
/*     */                   }
/*     */                 });
/*     */           }
/*     */         });
/*     */   }
/*     */   
/*     */   private void handleName(Player player, String[] args) {
/* 126 */     if (!player.hasPermission("nick.custom")) {
/* 127 */       player.sendMessage(this.messages.get("no-permission", new String[0]));
/*     */       return;
/*     */     } 
/* 130 */     if (args.length < 2) {
/* 131 */       player.sendMessage(this.messages.get("name-usage", new String[0]));
/*     */       return;
/*     */     } 
/* 134 */     this.bookGui.applyCustomName(player, args[1]);
/*     */   }
/*     */ 
/*     */   
/*     */   public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
/* 139 */     if (args.length != 1) return Collections.emptyList();
/*     */     
/* 141 */     List<String> options = new ArrayList<>();
/* 142 */     options.add("reset");
/* 143 */     if (sender.hasPermission("nick.skin")) options.add("skin"); 
/* 144 */     if (sender.hasPermission("nick.custom")) options.add("name");
/*     */     
/* 146 */     String typed = args[0].toLowerCase(Locale.ROOT);
/* 147 */     List<String> out = new ArrayList<>();
/* 148 */     for (String option : options) {
/* 149 */       if (option.startsWith(typed)) out.add(option); 
/*     */     } 
/* 151 */     return out;
/*     */   }
/*     */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\command\NickCommand.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */