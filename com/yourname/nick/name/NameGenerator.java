/*    */ package com.yourname.nick.name;
/*    */ 
/*    */ import java.util.List;
/*    */ import java.util.Optional;
/*    */ import java.util.concurrent.ThreadLocalRandom;
/*    */ import org.bukkit.configuration.file.YamlConfiguration;
/*    */ import org.bukkit.entity.Player;
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class NameGenerator
/*    */ {
/*    */   private static final int MAX_ATTEMPTS = 64;
/*    */   private static final int MAX_LENGTH = 16;
/*    */   private final List<String> adjectives;
/*    */   private final List<String> nouns;
/*    */   private final int maxNumber;
/*    */   private final NameValidator validator;
/*    */   
/*    */   public NameGenerator(YamlConfiguration names, NameValidator validator) {
/* 21 */     this.validator = validator;
/* 22 */     this.adjectives = names.getStringList("generator.adjectives");
/* 23 */     this.nouns = names.getStringList("generator.nouns");
/* 24 */     this.maxNumber = Math.max(1, names.getInt("generator.max-number", 99));
/*    */   }
/*    */ 
/*    */   
/*    */   public Optional<String> generate(Player requester) {
/* 29 */     if (this.adjectives.isEmpty() || this.nouns.isEmpty()) {
/* 30 */       return Optional.empty();
/*    */     }
/* 32 */     ThreadLocalRandom random = ThreadLocalRandom.current();
/* 33 */     for (int attempt = 0; attempt < 64; attempt++) {
/* 34 */       StringBuilder candidate = new StringBuilder();
/* 35 */       candidate.append(this.adjectives.get(random.nextInt(this.adjectives.size())));
/* 36 */       candidate.append(this.nouns.get(random.nextInt(this.nouns.size())));
/* 37 */       if (random.nextInt(3) != 0) {
/* 38 */         candidate.append(random.nextInt(1, this.maxNumber + 1));
/*    */       }
/* 40 */       String name = candidate.toString();
/* 41 */       if (name.length() <= 16 && this.validator.validate(name, requester) == NameValidator.Result.VALID) {
/* 42 */         return Optional.of(name);
/*    */       }
/*    */     } 
/* 45 */     return Optional.empty();
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\name\NameGenerator.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */