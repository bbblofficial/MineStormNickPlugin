package com.yourname.nick.name;

import java.util.List;
import java.util.Optional;
import java.util.concurrent.ThreadLocalRandom;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;



public final class NameGenerator
{
  private static final int MAX_ATTEMPTS = 64;
  private static final int MAX_LENGTH = 16;
  private final List<String> adjectives;
  private final List<String> nouns;
  private final int maxNumber;
  private final NameValidator validator;
  
  public NameGenerator(YamlConfiguration names, NameValidator validator) {
    this.validator = validator;
    this.adjectives = names.getStringList("generator.adjectives");
    this.nouns = names.getStringList("generator.nouns");
    this.maxNumber = Math.max(1, names.getInt("generator.max-number", 99));
  }

  
  public Optional<String> generate(Player requester) {
    if (this.adjectives.isEmpty() || this.nouns.isEmpty()) {
      return Optional.empty();
    }
    ThreadLocalRandom random = ThreadLocalRandom.current();
    for (int attempt = 0; attempt < 64; attempt++) {
      StringBuilder candidate = new StringBuilder();
      candidate.append(this.adjectives.get(random.nextInt(this.adjectives.size())));
      candidate.append(this.nouns.get(random.nextInt(this.nouns.size())));
      if (random.nextInt(3) != 0) {
        candidate.append(random.nextInt(1, this.maxNumber + 1));
      }
      String name = candidate.toString();
      if (name.length() <= 16 && this.validator.validate(name, requester) == NameValidator.Result.VALID) {
        return Optional.of(name);
      }
    } 
    return Optional.empty();
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\name\NameGenerator.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */