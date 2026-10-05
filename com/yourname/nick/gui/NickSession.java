package com.yourname.nick.gui;
import com.yourname.nick.model.NickRecord;
import com.yourname.nick.model.Rank;
import com.yourname.nick.model.SkinData;

public final class NickSession {
  private final NickRecord history;
  
  public enum Step {
    RANK, SKIN, NAME, ROLLER;
  }
  
  private Step step = Step.RANK;
  private Rank rank = Rank.DEFAULT;
  private SkinData skin = SkinData.normal();
  private String pendingName;
  
  public NickSession(NickRecord history) {
    this.history = history;
  }
  
  public NickRecord history() { return this.history; }
  public Step step() { return this.step; }
  public void step(Step newStep) { this.step = newStep; }
  public Rank rank() { return this.rank; }
  public void rank(Rank newRank) { this.rank = newRank; }
  public SkinData skin() { return this.skin; }
  public void skin(SkinData newSkin) { this.skin = newSkin; }
  public String pendingName() { return this.pendingName; } public void pendingName(String name) {
    this.pendingName = name;
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\gui\NickSession.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */