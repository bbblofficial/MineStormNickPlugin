/*    */ package com.yourname.nick.model;
/*    */ 
/*    */ import java.util.Locale;
/*    */ import java.util.Optional;
/*    */ import org.bukkit.ChatColor;
/*    */ 
/*    */ public enum Rank
/*    */ {
/*  9 */   DEFAULT("DEFAULT", ChatColor.GRAY, null),
/* 10 */   VIP("VIP", ChatColor.GREEN, null),
/* 11 */   VIP_PLUS("VIP", ChatColor.GREEN, ChatColor.GOLD),
/* 12 */   MVP("MVP", ChatColor.AQUA, null),
/* 13 */   MVP_PLUS("MVP", ChatColor.AQUA, ChatColor.RED);
/*    */   
/*    */   private final String base;
/*    */   private final ChatColor color;
/*    */   private final ChatColor plusColor;
/*    */   
/*    */   Rank(String base, ChatColor color, ChatColor plusColor) {
/* 20 */     this.base = base;
/* 21 */     this.color = color;
/* 22 */     this.plusColor = plusColor;
/*    */   }
/*    */   
/* 25 */   public ChatColor nameColor() { return this.color; } public ChatColor getNameColor() {
/* 26 */     return this.color;
/*    */   }
/*    */   public String label() {
/* 29 */     return (this.plusColor == null) ? this.base : (this.base + "+");
/*    */   }
/*    */ 
/*    */   
/*    */   public String prefix() {
/* 34 */     if (this == DEFAULT) return ""; 
/* 35 */     StringBuilder sb = new StringBuilder();
/* 36 */     sb.append(this.color).append('[').append(this.base);
/* 37 */     if (this.plusColor != null) sb.append(this.plusColor).append('+'); 
/* 38 */     sb.append(this.color).append(']').append(ChatColor.RESET).append(' ');
/* 39 */     return sb.toString();
/*    */   }
/*    */   
/*    */   public String tag() {
/* 43 */     if (this == DEFAULT) return ""; 
/* 44 */     return prefix().trim();
/*    */   }
/*    */   
/*    */   public String pickerLabel() {
/* 48 */     if (this == DEFAULT) return this.color + "DEFAULT"; 
/* 49 */     return prefix().trim();
/*    */   }
/*    */   
/*    */   public String styledName(String name) {
/* 53 */     return prefix() + this.color + name + ChatColor.RESET;
/*    */   }
/*    */   
/*    */   public static Optional<Rank> parse(String input) {
/* 57 */     if (input == null || input.trim().isEmpty()) return Optional.empty(); 
/* 58 */     String trimmed = input.trim();
/* 59 */     String normalized = trimmed.toUpperCase(Locale.ROOT).replace("+", "_PLUS");
/* 60 */     for (Rank rank : values()) {
/* 61 */       if (rank.name().equals(normalized) || rank.label().equalsIgnoreCase(trimmed)) {
/* 62 */         return Optional.of(rank);
/*    */       }
/*    */     } 
/* 65 */     return Optional.empty();
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\Rank.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */