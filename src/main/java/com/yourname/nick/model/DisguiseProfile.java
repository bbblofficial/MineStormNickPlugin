package com.yourname.nick.model;

import java.util.UUID;



public final class DisguiseProfile
{
  private final UUID realUuid;
  private final String realName;
  private final String nickname;
  private final Rank rank;
  private final SkinData skin;
  private final int stars;
  private final boolean active;
  private final String originalDisplayName;
  
  public DisguiseProfile(UUID realUuid, String realName, String nickname, Rank rank, SkinData skin, int stars, boolean active, String originalDisplayName) {
    this.realUuid = realUuid;
    this.realName = realName;
    this.nickname = nickname;
    this.rank = rank;
    this.skin = skin;
    this.stars = stars;
    this.active = active;
    this.originalDisplayName = originalDisplayName;
  }
  
  public UUID getRealUuid() { return this.realUuid; }
  public String getRealName() { return this.realName; }
  public String getNickname() { return this.nickname; }
  public Rank getRank() { return this.rank; }
  public SkinData getSkin() { return this.skin; }
  public int getStars() { return this.stars; }
  public boolean isActive() { return this.active; } public String getOriginalDisplayName() {
    return this.originalDisplayName;
  }
  
  public UUID realUuid() { return this.realUuid; }
  public String realName() { return this.realName; }
  public String nickname() { return this.nickname; }
  public Rank rank() { return this.rank; }
  public SkinData skin() { return this.skin; }
  public int stars() { return this.stars; }
  public boolean active() { return this.active; } public String originalDisplayName() {
    return this.originalDisplayName;
  }
  public DisguiseProfile withActive(boolean newActive) {
    return new DisguiseProfile(this.realUuid, this.realName, this.nickname, this.rank, this.skin, this.stars, newActive, this.originalDisplayName);
  }
  
  public DisguiseProfile withSkin(SkinData newSkin) {
    return new DisguiseProfile(this.realUuid, this.realName, this.nickname, this.rank, newSkin, this.stars, this.active, this.originalDisplayName);
  }

  
  public String styledName() {
    return this.rank.styledName(this.nickname);
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\DisguiseProfile.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */