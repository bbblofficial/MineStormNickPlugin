/*    */ package com.yourname.nick.model;
/*    */ 
/*    */ import java.util.UUID;
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class DisguiseProfile
/*    */ {
/*    */   private final UUID realUuid;
/*    */   private final String realName;
/*    */   private final String nickname;
/*    */   private final Rank rank;
/*    */   private final SkinData skin;
/*    */   private final int stars;
/*    */   private final boolean active;
/*    */   private final String originalDisplayName;
/*    */   
/*    */   public DisguiseProfile(UUID realUuid, String realName, String nickname, Rank rank, SkinData skin, int stars, boolean active, String originalDisplayName) {
/* 19 */     this.realUuid = realUuid;
/* 20 */     this.realName = realName;
/* 21 */     this.nickname = nickname;
/* 22 */     this.rank = rank;
/* 23 */     this.skin = skin;
/* 24 */     this.stars = stars;
/* 25 */     this.active = active;
/* 26 */     this.originalDisplayName = originalDisplayName;
/*    */   }
/*    */   
/* 29 */   public UUID getRealUuid() { return this.realUuid; }
/* 30 */   public String getRealName() { return this.realName; }
/* 31 */   public String getNickname() { return this.nickname; }
/* 32 */   public Rank getRank() { return this.rank; }
/* 33 */   public SkinData getSkin() { return this.skin; }
/* 34 */   public int getStars() { return this.stars; }
/* 35 */   public boolean isActive() { return this.active; } public String getOriginalDisplayName() {
/* 36 */     return this.originalDisplayName;
/*    */   }
/*    */   
/* 39 */   public UUID realUuid() { return this.realUuid; }
/* 40 */   public String realName() { return this.realName; }
/* 41 */   public String nickname() { return this.nickname; }
/* 42 */   public Rank rank() { return this.rank; }
/* 43 */   public SkinData skin() { return this.skin; }
/* 44 */   public int stars() { return this.stars; }
/* 45 */   public boolean active() { return this.active; } public String originalDisplayName() {
/* 46 */     return this.originalDisplayName;
/*    */   }
/*    */   public DisguiseProfile withActive(boolean newActive) {
/* 49 */     return new DisguiseProfile(this.realUuid, this.realName, this.nickname, this.rank, this.skin, this.stars, newActive, this.originalDisplayName);
/*    */   }
/*    */   
/*    */   public DisguiseProfile withSkin(SkinData newSkin) {
/* 53 */     return new DisguiseProfile(this.realUuid, this.realName, this.nickname, this.rank, newSkin, this.stars, this.active, this.originalDisplayName);
/*    */   }
/*    */ 
/*    */   
/*    */   public String styledName() {
/* 58 */     return this.rank.styledName(this.nickname);
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\DisguiseProfile.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */