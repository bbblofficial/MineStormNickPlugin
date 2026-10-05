/*    */ package com.yourname.nick.model;
/*    */ 
/*    */ import java.util.UUID;
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class NickRecord
/*    */ {
/*    */   private final UUID realUuid;
/*    */   private final String realName;
/*    */   private final String nickname;
/*    */   private final String rankUsed;
/*    */   private final String skinSource;
/*    */   private final String skinValue;
/*    */   private final String skinSignature;
/*    */   private final String action;
/*    */   private final long createdAt;
/*    */   private final String ip;
/*    */   
/*    */   public NickRecord(UUID realUuid, String realName, String nickname, String rankUsed, String skinSource, String skinValue, String skinSignature, String action, long createdAt, String ip) {
/* 21 */     this.realUuid = realUuid;
/* 22 */     this.realName = realName;
/* 23 */     this.nickname = nickname;
/* 24 */     this.rankUsed = rankUsed;
/* 25 */     this.skinSource = skinSource;
/* 26 */     this.skinValue = skinValue;
/* 27 */     this.skinSignature = skinSignature;
/* 28 */     this.action = action;
/* 29 */     this.createdAt = createdAt;
/* 30 */     this.ip = ip;
/*    */   }
/*    */   
/* 33 */   public UUID realUuid() { return this.realUuid; }
/* 34 */   public UUID getRealUuid() { return this.realUuid; }
/* 35 */   public String realName() { return this.realName; }
/* 36 */   public String getRealName() { return this.realName; }
/* 37 */   public String nickname() { return this.nickname; }
/* 38 */   public String getNickname() { return this.nickname; }
/* 39 */   public String rankUsed() { return this.rankUsed; }
/* 40 */   public String getRankUsed() { return this.rankUsed; }
/* 41 */   public String skinSource() { return this.skinSource; }
/* 42 */   public String getSkinSource() { return this.skinSource; }
/* 43 */   public String skinValue() { return this.skinValue; }
/* 44 */   public String getSkinValue() { return this.skinValue; }
/* 45 */   public String skinSignature() { return this.skinSignature; }
/* 46 */   public String getSkinSignature() { return this.skinSignature; }
/* 47 */   public String action() { return this.action; }
/* 48 */   public String getAction() { return this.action; }
/* 49 */   public long createdAt() { return this.createdAt; }
/* 50 */   public long getCreatedAt() { return this.createdAt; }
/* 51 */   public String ip() { return this.ip; } public String getIp() {
/* 52 */     return this.ip;
/*    */   }
/*    */   public SkinData toSkinData() {
/* 55 */     return SkinData.fromStorage(this.skinSource, this.skinValue, this.skinSignature);
/*    */   }
/*    */   
/*    */   public Rank rank() {
/* 59 */     return Rank.parse(this.rankUsed).orElse(Rank.DEFAULT);
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\NickRecord.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */