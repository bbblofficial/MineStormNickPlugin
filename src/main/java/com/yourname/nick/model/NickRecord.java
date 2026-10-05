package com.yourname.nick.model;

import java.util.UUID;



public final class NickRecord
{
  private final UUID realUuid;
  private final String realName;
  private final String nickname;
  private final String rankUsed;
  private final String skinSource;
  private final String skinValue;
  private final String skinSignature;
  private final String action;
  private final long createdAt;
  private final String ip;
  
  public NickRecord(UUID realUuid, String realName, String nickname, String rankUsed, String skinSource, String skinValue, String skinSignature, String action, long createdAt, String ip) {
    this.realUuid = realUuid;
    this.realName = realName;
    this.nickname = nickname;
    this.rankUsed = rankUsed;
    this.skinSource = skinSource;
    this.skinValue = skinValue;
    this.skinSignature = skinSignature;
    this.action = action;
    this.createdAt = createdAt;
    this.ip = ip;
  }
  
  public UUID realUuid() { return this.realUuid; }
  public UUID getRealUuid() { return this.realUuid; }
  public String realName() { return this.realName; }
  public String getRealName() { return this.realName; }
  public String nickname() { return this.nickname; }
  public String getNickname() { return this.nickname; }
  public String rankUsed() { return this.rankUsed; }
  public String getRankUsed() { return this.rankUsed; }
  public String skinSource() { return this.skinSource; }
  public String getSkinSource() { return this.skinSource; }
  public String skinValue() { return this.skinValue; }
  public String getSkinValue() { return this.skinValue; }
  public String skinSignature() { return this.skinSignature; }
  public String getSkinSignature() { return this.skinSignature; }
  public String action() { return this.action; }
  public String getAction() { return this.action; }
  public long createdAt() { return this.createdAt; }
  public long getCreatedAt() { return this.createdAt; }
  public String ip() { return this.ip; } public String getIp() {
    return this.ip;
  }
  public SkinData toSkinData() {
    return SkinData.fromStorage(this.skinSource, this.skinValue, this.skinSignature);
  }
  
  public Rank rank() {
    return Rank.parse(this.rankUsed).orElse(Rank.DEFAULT);
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\NickRecord.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */