# project-codemetrics
I wanted a project that could give me some development metrics.  Codex was able to quickly generate a file that counts how many source files, lines of code, etc are in a folder, counted recursively.  This way I can track how much code was created in an easy manner along with some other useful metrics.

The initial files generated didn't know to exclude themselves, so the project counter code was always inflated with the source of the tool.  This iteration fixes that, and in fact shows "Tool files excluded: 2", which is correct.  This was validated by running the source counter tool within a folder that only had the source counter tool, and the resulting LOC showed zero.


Here is some example output of the tool when run against my current "people" project.  Note that I have altered some of the output manually to hide things like my machine name and the directory structure on my machine for security purposes.

This project took less than an hour from initial description typed into ChatGPT to when I pushed the files to GitHub.  I didn't have timestamps displayed and found that they aren't tracked by ChatGPT, but I am adding them to my ChatGPT now so I can better track how long projects take in the future.

<prompt> project-people-basic % ./projmetrics.sh 

Root: /<Dir Structure Hidden>/Coding Projects/people/project-people-basic
Profile: all
Files counted: 43
Total size: 95.1 KB
Text files skipped (binary/unreadable): 0
Tool files excluded: 2

Line counts (heuristic):
  Total:   2578
  Code:    2204
  Comment: 5
  Blank:   369

By extension:
  .java      files=    33  lines=     2379  code=     2038  cmt=        0  blank=      341
  .sh        files=     5  lines=       28  code=       16  cmt=        5  blank=        7
  .xml       files=     4  lines=      129  code=      115  cmt=        0  blank=       14
  .md        files=     1  lines=       42  code=       35  cmt=        0  blank=        7

Top 10 largest files:
    13.0 KB  people-core/src/main/java/com/people/service/PeopleService.java
    12.7 KB  people-cli/src/main/java/com/people/cli/commands/PersonCommand.java
     9.4 KB  people-cli/src/main/java/com/people/cli/commands/AddressCommand.java
     8.1 KB  people-cli/src/main/java/com/people/cli/commands/EmploymentCommand.java
     8.0 KB  people-tests/src/test/java/com/people/tests/PeopleServiceTest.java
     6.4 KB  people-core/src/main/java/com/people/service/Validators.java
     5.2 KB  people-cli/src/main/java/com/people/cli/commands/RelationshipCommand.java
     4.5 KB  people-cli/src/main/java/com/people/cli/SeedData.java
     2.6 KB  people-cli/src/main/java/com/people/cli/CliArgs.java
     2.4 KB  people-core/src/main/java/com/people/repo/InMemoryRelationshipRepository.java

Top 10 longest files (by total lines):
        340 lines  people-core/src/main/java/com/people/service/PeopleService.java
        282 lines  people-cli/src/main/java/com/people/cli/commands/PersonCommand.java
        205 lines  people-cli/src/main/java/com/people/cli/commands/AddressCommand.java
        202 lines  people-tests/src/test/java/com/people/tests/PeopleServiceTest.java
        181 lines  people-cli/src/main/java/com/people/cli/commands/EmploymentCommand.java
        141 lines  people-core/src/main/java/com/people/service/Validators.java
        125 lines  people-cli/src/main/java/com/people/cli/commands/RelationshipCommand.java
        107 lines  people-cli/src/main/java/com/people/cli/SeedData.java
         77 lines  people-cli/src/main/java/com/people/cli/CliArgs.java
         74 lines  people-core/src/main/java/com/people/repo/InMemoryEmploymentRepository.java

