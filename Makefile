CC = gcc
CFLAGS = -Wall -g -Isrc/include -Itests -MMD -fsanitize=address -g
CFLAGS_NO_ASAN = -Wall -g -Isrc/include -Itests -MMD
SRCDIR = src
OBJDIR = obj
BINDIR = bin
TARGET_ASAN = $(BINDIR)/Eigen
TARGET_NO_ASAN = $(BINDIR)/Eigen_no_asan

SRC = $(SRCDIR)/main.c \
      $(SRCDIR)/utils.c \
      $(SRCDIR)/builtins.c \
      $(SRCDIR)/linenoise.c \
      $(SRCDIR)/hashmap.c \
      $(SRCDIR)/job.c

OBJ_ASAN = $(SRC:$(SRCDIR)/%.c=$(OBJDIR)/asan_%.o)
OBJ_NO_ASAN = $(SRC:$(SRCDIR)/%.c=$(OBJDIR)/noasan_%.o)
DEP_ASAN = $(OBJ_ASAN:.o=.d)
DEP_NO_ASAN = $(OBJ_NO_ASAN:.o=.d)

all: $(TARGET_ASAN)

$(TARGET_ASAN): $(OBJ_ASAN)
	@mkdir -p $(BINDIR)
	$(CC) $(CFLAGS) -o $(TARGET_ASAN) $(OBJ_ASAN)

$(TARGET_NO_ASAN): $(OBJ_NO_ASAN)
	@mkdir -p $(BINDIR)
	$(CC) $(CFLAGS_NO_ASAN) -o $(TARGET_NO_ASAN) $(OBJ_NO_ASAN)

$(OBJDIR)/asan_%.o: $(SRCDIR)/%.c
	@mkdir -p $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJDIR)/noasan_%.o: $(SRCDIR)/%.c
	@mkdir -p $(OBJDIR)
	$(CC) $(CFLAGS_NO_ASAN) -c $< -o $@

ifneq ($(wildcard $(OBJDIR)/*.d),)
-include $(OBJ_ASAN:.o=.d) $(OBJ_NO_ASAN:.o=.d)
endif

clean:
	rm -rf $(OBJDIR) $(BINDIR)

leak: $(TARGET_NO_ASAN)
	@echo "Built without ASan. To check for leaks:"
	@echo "  MallocStackLogging=1 leaks --atExit -- ./bin/Eigen_no_asan"

.PHONY: all clean leak