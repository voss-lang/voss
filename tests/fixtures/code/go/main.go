package main

import "fmt"

func sharedEntry(x int) int {
	return helperValue(x) + 1
}

func helperValue(n int) int {
	return n * 2
}

type HelperStruct struct {
	Value int
}

func main() {
	fmt.Println(sharedEntry(41))
}
