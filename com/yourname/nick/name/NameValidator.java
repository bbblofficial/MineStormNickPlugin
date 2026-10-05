/*    */ package com.yourname.nick.name;
/*    */ 
/*    */ import com.yourname.nick.disguise.DisguiseRegistry;
/*    */ import java.util.ArrayList;
/*    */ import java.util.Collections;
/*    */ import java.util.HashSet;
/*    */ import java.util.List;
/*    */ import java.util.Locale;
/*    */ import java.util.Set;
/*    */ import java.util.regex.Pattern;
/*    */ import org.bukkit.Bukkit;
/*    */ import org.bukkit.configuration.file.YamlConfiguration;
/*    */ import org.bukkit.entity.Player;
/*    */ 
/*    */ public final class NameValidator
/*    */ {
/*    */   public enum Result
/*    */   {
/* 19 */     VALID, INVALID_FORMAT, RESERVED, IN_USE, OWN_NAME;
/*    */   }
/* 21 */   private static final Pattern MOJANG_NAME = Pattern.compile("^[A-Za-z0-9_]{3,16}$");
/*    */   
/*    */   private final Set<String> reserved;
/*    */   private final List<String> reservedFragments;
/*    */   private final DisguiseRegistry registry;
/*    */   
/*    */   public NameValidator(YamlConfiguration names, DisguiseRegistry registry) {
/* 28 */     this.registry = registry;
/*    */     
/* 30 */     Set<String> lowerReserved = new HashSet<>();
/* 31 */     for (String value : names.getStringList("reserved")) {
/* 32 */       if (value != null) lowerReserved.add(value.toLowerCase(Locale.ROOT)); 
/*    */     } 
/* 34 */     this.reserved = Collections.unmodifiableSet(lowerReserved);
/*    */     
/* 36 */     List<String> fragments = new ArrayList<>();
/* 37 */     for (String value : names.getStringList("reserved-fragments")) {
/* 38 */       if (value == null)
/* 39 */         continue;  String trimmed = value.toLowerCase(Locale.ROOT).trim();
/* 40 */       if (!trimmed.isEmpty()) fragments.add(trimmed); 
/*    */     } 
/* 42 */     this.reservedFragments = Collections.unmodifiableList(fragments);
/*    */   }
/*    */   
/*    */   public static boolean isValidFormat(String name) {
/* 46 */     return (name != null && MOJANG_NAME.matcher(name).matches());
/*    */   }
/*    */   
/*    */   public Result validate(String name, Player requester) {
/* 50 */     if (!isValidFormat(name)) return Result.INVALID_FORMAT; 
/* 51 */     String lower = name.toLowerCase(Locale.ROOT);
/* 52 */     if (this.reserved.contains(lower)) return Result.RESERVED; 
/* 53 */     for (String fragment : this.reservedFragments) {
/* 54 */       if (lower.contains(fragment)) return Result.RESERVED; 
/*    */     } 
/* 56 */     if (name.equalsIgnoreCase(requester.getName())) return Result.OWN_NAME; 
/* 57 */     Player online = Bukkit.getPlayerExact(name);
/* 58 */     if (online != null && !online.getUniqueId().equals(requester.getUniqueId())) {
/* 59 */       return Result.IN_USE;
/*    */     }
/* 61 */     if (this.registry.isNickInUse(name, requester.getUniqueId())) return Result.IN_USE; 
/* 62 */     return Result.VALID;
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\name\NameValidator.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */