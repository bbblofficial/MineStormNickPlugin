/*     */ package com.yourname.nick.command;
/*     */ 
/*     */ import com.yourname.nick.NickPlugin;
/*     */ import com.yourname.nick.disguise.DisguiseRegistry;
/*     */ import com.yourname.nick.message.Messages;
/*     */ import com.yourname.nick.model.DisguiseProfile;
/*     */ import com.yourname.nick.model.NickRecord;
/*     */ import com.yourname.nick.name.NameValidator;
/*     */ import com.yourname.nick.storage.StorageManager;
/*     */ import com.yourname.nick.util.Async;
/*     */ import java.time.Instant;
/*     */ import java.time.ZoneOffset;
/*     */ import java.time.format.DateTimeFormatter;
/*     */ import java.util.ArrayList;
/*     */ import java.util.Collections;
/*     */ import java.util.List;
/*     */ import java.util.Locale;
/*     */ import java.util.Optional;
/*     */ import java.util.function.BiConsumer;
/*     */ import org.bukkit.command.Command;
/*     */ import org.bukkit.command.CommandSender;
/*     */ import org.bukkit.command.TabExecutor;
/*     */ import org.bukkit.plugin.Plugin;
/*     */ 
/*     */ public final class RealNameCommand
/*     */   implements TabExecutor
/*     */ {
/*  28 */   private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm 'UTC'").withZone(ZoneOffset.UTC);
/*     */   
/*     */   private final NickPlugin plugin;
/*     */   private final Messages messages;
/*     */   private final DisguiseRegistry registry;
/*     */   private final StorageManager storage;
/*     */   
/*     */   public RealNameCommand(NickPlugin plugin, Messages messages, DisguiseRegistry registry, StorageManager storage) {
/*  36 */     this.plugin = plugin;
/*  37 */     this.messages = messages;
/*  38 */     this.registry = registry;
/*  39 */     this.storage = storage;
/*     */   }
/*     */ 
/*     */   
/*     */   public boolean onCommand(final CommandSender sender, Command command, String label, String[] args) {
/*  44 */     if (!sender.hasPermission("nick.staff")) {
/*  45 */       sender.sendMessage(this.messages.get("no-permission", new String[0]));
/*  46 */       return true;
/*     */     } 
/*  48 */     if (args.length != 1) {
/*  49 */       sender.sendMessage(this.messages.get("realname-usage", new String[0]));
/*  50 */       return true;
/*     */     } 
/*  52 */     final String nick = args[0];
/*  53 */     if (!NameValidator.isValidFormat(nick)) {
/*  54 */       sender.sendMessage(this.messages.get("realname-none", new String[] { "nick", nick }));
/*  55 */       return true;
/*     */     } 
/*     */     
/*  58 */     Optional<DisguiseProfile> live = this.registry.findByNick(nick);
/*  59 */     if (live.isPresent()) {
/*  60 */       DisguiseProfile profile = live.get();
/*  61 */       sender.sendMessage(this.messages.get("realname-live", new String[] { "nick", profile
/*  62 */               .nickname(), "real", profile
/*  63 */               .realName(), "uuid", profile
/*  64 */               .realUuid().toString(), "state", 
/*  65 */               profile.active() ? "active" : "dormant" }));
/*  66 */       return true;
/*     */     } 
/*     */     
/*  69 */     this.storage.findLatestByNickname(nick).whenComplete(new BiConsumer<Optional<NickRecord>, Throwable>()
/*     */         {
/*     */           public void accept(final Optional<NickRecord> row, final Throwable error)
/*     */           {
/*  73 */             Async.main((Plugin)RealNameCommand.this.plugin, new Runnable()
/*     */                 {
/*     */                   public void run() {
/*  76 */                     if (error != null) {
/*  77 */                       sender.sendMessage(RealNameCommand.this.messages.get("storage-error", new String[0]));
/*     */                       return;
/*     */                     } 
/*  80 */                     if (!row.isPresent()) {
/*  81 */                       sender.sendMessage(RealNameCommand.this.messages.get("realname-none", new String[] { "nick", this.this$1.val$nick }));
/*     */                       return;
/*     */                     } 
/*  84 */                     NickRecord record = row.get();
/*  85 */                     sender.sendMessage(RealNameCommand.this.messages.get("realname-historical", new String[] { "nick", record
/*  86 */                             .nickname(), "real", record
/*  87 */                             .realName(), "uuid", record
/*  88 */                             .realUuid().toString(), "date", 
/*  89 */                             RealNameCommand.access$200().format(Instant.ofEpochMilli(record.createdAt())) }));
/*     */                   }
/*     */                 });
/*     */           }
/*     */         });
/*  94 */     return true;
/*     */   }
/*     */ 
/*     */   
/*     */   public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
/*  99 */     if (args.length != 1 || !sender.hasPermission("nick.staff")) {
/* 100 */       return Collections.emptyList();
/*     */     }
/* 102 */     String typed = args[0].toLowerCase(Locale.ROOT);
/* 103 */     List<String> out = new ArrayList<>();
/* 104 */     for (DisguiseProfile profile : this.registry.all()) {
/* 105 */       String n = profile.nickname();
/* 106 */       if (n != null && n.toLowerCase(Locale.ROOT).startsWith(typed)) out.add(n); 
/*     */     } 
/* 108 */     return out;
/*     */   }
/*     */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\command\RealNameCommand.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */