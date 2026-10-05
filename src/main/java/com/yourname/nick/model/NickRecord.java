package com.yourname.nick.model;

import java.util.UUID;

/**
 * One persisted row of nick history. The Rank column is no longer
 * part of the API; older databases keep the column but its value is
 * ignored on read and written as "NONE" on insert (see StorageManager).
 */
public final class NickRecord {

    private final UUID realUuid;
    private final String realName;
    private final String nickname;
    private final String skinSource;
    private final String skinValue;
    private final String skinSignature;
    private final String action;
    private final long createdAt;
    private final String ip;

    public NickRecord(UUID realUuid,
                      String realName,
                      String nickname,
                      String skinSource,
                      String skinValue,
                      String skinSignature,
                      String action,
                      long createdAt,
                      String ip) {
        this.realUuid = realUuid;
        this.realName = realName;
        this.nickname = nickname;
        this.skinSource = skinSource;
        this.skinValue = skinValue;
        this.skinSignature = skinSignature;
        this.action = action;
        this.createdAt = createdAt;
        this.ip = ip;
    }

    public UUID realUuid()           { return this.realUuid; }
    public String realName()         { return this.realName; }
    public String nickname()         { return this.nickname; }
    public String skinSource()       { return this.skinSource; }
    public String skinValue()        { return this.skinValue; }
    public String skinSignature()    { return this.skinSignature; }
    public String action()           { return this.action; }
    public long createdAt()          { return this.createdAt; }
    public String ip()               { return this.ip; }

    /* Legacy getters. */
    public UUID getRealUuid()        { return this.realUuid; }
    public String getRealName()      { return this.realName; }
    public String getNickname()      { return this.nickname; }
    public String getSkinSource()    { return this.skinSource; }
    public String getSkinValue()     { return this.skinValue; }
    public String getSkinSignature() { return this.skinSignature; }
    public String getAction()        { return this.action; }
    public long getCreatedAt()       { return this.createdAt; }
    public String getIp()            { return this.ip; }

    public SkinData toSkinData() {
        return SkinData.fromStorage(this.skinSource, this.skinValue, this.skinSignature);
    }
}
