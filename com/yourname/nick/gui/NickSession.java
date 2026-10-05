/*    */ package com.yourname.nick.gui;
/*    */ import com.yourname.nick.model.NickRecord;
/*    */ import com.yourname.nick.model.Rank;
/*    */ import com.yourname.nick.model.SkinData;
/*    */ 
/*    */ public final class NickSession {
/*    */   private final NickRecord history;
/*    */   
/*    */   public enum Step {
/* 10 */     RANK, SKIN, NAME, ROLLER;
/*    */   }
/*    */   
/* 13 */   private Step step = Step.RANK;
/* 14 */   private Rank rank = Rank.DEFAULT;
/* 15 */   private SkinData skin = SkinData.normal();
/*    */   private String pendingName;
/*    */   
/*    */   public NickSession(NickRecord history) {
/* 19 */     this.history = history;
/*    */   }
/*    */   
/* 22 */   public NickRecord history() { return this.history; }
/* 23 */   public Step step() { return this.step; }
/* 24 */   public void step(Step newStep) { this.step = newStep; }
/* 25 */   public Rank rank() { return this.rank; }
/* 26 */   public void rank(Rank newRank) { this.rank = newRank; }
/* 27 */   public SkinData skin() { return this.skin; }
/* 28 */   public void skin(SkinData newSkin) { this.skin = newSkin; }
/* 29 */   public String pendingName() { return this.pendingName; } public void pendingName(String name) {
/* 30 */     this.pendingName = name;
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\gui\NickSession.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */