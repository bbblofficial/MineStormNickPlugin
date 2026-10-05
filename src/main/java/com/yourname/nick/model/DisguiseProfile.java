package com.yourname.nick.model;

import java.util.UUID;

/**
 * Immutable snapshot of a player's current nickname state.
 * The Rank concept was removed entirely; the visible name is now
 * exactly the nickname that was chosen.
 */
public final class DisguiseProfile {

    private final UUID realUuid;
    private final String realName;
    private final String nickname;
    private final SkinData skin;
    private final int stars;
    private final boolean active;
    private final String originalDisplayName;

    public DisguiseProfile(UUID realUuid,
                           String realName,
                           String nickname,
                           SkinData skin,
                           int stars,
                           boolean active,
                           String originalDisplayName) {
        this.realUuid = realUuid;
        this.realName = realName;
        this.nickname = nickname;
        this.skin = skin;
        this.stars = stars;
        this.active = active;
        this.originalDisplayName = originalDisplayName;
    }

    public UUID realUuid()             { return this.realUuid; }
    public String realName()           { return this.realName; }
    public String nickname()           { return this.nickname; }
    public SkinData skin()             { return this.skin; }
    public int stars()                 { return this.stars; }
    public boolean active()            { return this.active; }
    public String originalDisplayName(){ return this.originalDisplayName; }

    /* Legacy-style getters kept for binary compatibility. */
    public UUID getRealUuid()              { return this.realUuid; }
    public String getRealName()            { return this.realName; }
    public String getNickname()            { return this.nickname; }
    public SkinData getSkin()              { return this.skin; }
    public int getStars()                  { return this.stars; }
    public boolean isActive()              { return this.active; }
    public String getOriginalDisplayName() { return this.originalDisplayName; }

    public DisguiseProfile withActive(boolean newActive) {
        return new DisguiseProfile(this.realUuid, this.realName, this.nickname,
                this.skin, this.stars, newActive, this.originalDisplayName);
    }

    public DisguiseProfile withSkin(SkinData newSkin) {
        return new DisguiseProfile(this.realUuid, this.realName, this.nickname,
                newSkin, this.stars, this.active, this.originalDisplayName);
    }

    /** The display name is simply the nickname now. */
    public String styledName() {
        return this.nickname;
    }
}
