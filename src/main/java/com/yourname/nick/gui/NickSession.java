package com.yourname.nick.gui;

import com.yourname.nick.model.NickRecord;
import com.yourname.nick.model.SkinData;

/**
 * Short-lived GUI session. The Rank step was removed; the flow is now
 * skin -> name -> (optional roller) -> apply.
 */
public final class NickSession {

    public enum Step { SKIN, NAME, ROLLER }

    private final NickRecord history;
    private Step step = Step.SKIN;
    private SkinData skin = SkinData.normal();
    private String pendingName;

    public NickSession(NickRecord history) {
        this.history = history;
    }

    public NickRecord history() { return this.history; }
    public Step step()          { return this.step; }
    public void step(Step s)    { this.step = s; }
    public SkinData skin()      { return this.skin; }
    public void skin(SkinData s){ this.skin = s; }
    public String pendingName() { return this.pendingName; }
    public void pendingName(String name) { this.pendingName = name; }
}
