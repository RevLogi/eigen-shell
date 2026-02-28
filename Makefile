CC = gcc
CFLAGS = -Wall -g -Isrc/include
SRCDIR = src
OBJDIR = obj
BINDIR = bin
TARGET = $(BINDIR)/Eigen

SRC = $(SRCDIR)/main.c $(SRCDIR)/utils.c $(SRCDIR)/builtins.c $(SRCDIR)/linenoise.c $(SRCDIR)/hashmap.c
OBJ = $(OBJDIR)/main.o $(OBJDIR)/utils.o $(OBJDIR)/builtins.o $(OBJDIR)/linenoise.o $(OBJDIR)/hashmap.o

# Create directories if they don't exist
$(OBJDIR) $(BINDIR):
	mkdir -p $@

$(TARGET): | $(OBJDIR) $(BINDIR) $(OBJ)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJ)

$(OBJDIR)/main.o: $(SRCDIR)/main.c $(SRCDIR)/include/eigen.h $(SRCDIR)/include/builtins.h $(SRCDIR)/include/hashmap.h
	$(CC) $(CFLAGS) -c $(SRCDIR)/main.c -o $(OBJDIR)/main.o

$(OBJDIR)/utils.o: $(SRCDIR)/utils.c $(SRCDIR)/include/eigen.h
	$(CC) $(CFLAGS) -c $(SRCDIR)/utils.c -o $(OBJDIR)/utils.o

$(OBJDIR)/builtins.o: $(SRCDIR)/builtins.c $(SRCDIR)/include/eigen.h $(SRCDIR)/include/builtins.h $(SRCDIR)/include/hashmap.h
	$(CC) $(CFLAGS) -c $(SRCDIR)/builtins.c -o $(OBJDIR)/builtins.o

$(OBJDIR)/linenoise.o: $(SRCDIR)/linenoise.c $(SRCDIR)/include/linenoise.h
	$(CC) $(CFLAGS) -c $(SRCDIR)/linenoise.c -o $(OBJDIR)/linenoise.o

$(OBJDIR)/hashmap.o: $(SRCDIR)/hashmap.c $(SRCDIR)/include/hashmap.h
	$(CC) $(CFLAGS) -c $(SRCDIR)/hashmap.c -o $(OBJDIR)/hashmap.o

clean:
	rm -f $(OBJDIR)/*.o $(TARGET)

.PHONY: clean
