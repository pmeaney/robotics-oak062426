Ok, I have the A3144's installed into the system. They're ready to test.

Let's write a doc called gantry-limitation-shelf-dimensions-testing-tickets.md

Into it, let's write the first ticket.

This ticket needs to do soemthing like:





check each A3144 individually



give me time to place a magnet next to it, and see the change take place from 0 to 1 or 1 to 0 or whatever it will show up as in the live data, in the terminal



the ticket will explain the above bullet points-- including "ok, now hold a magnet up to each. check different magnet strengths, sizes, and proximities. Position each magnet with a little extra space to spare from the red zone.

Ticket 2 will be something like:





Now we'll test each main use case for the sensors (each vertical's top & bottom Z1T Z1B Z2T Z2B. horizontal gantry's left & right X1L X1R -- keep it X1 b/c X all alone is vague, as an abbreviation for the horizontal gantry)



test each vertical's end, and test 'walking back' of its gantry(s) which got too close





Ticket 3 will be something like:





Determine the distance between the distal ends of each green zone-- Z1, Z2, X1.



Determine the yellow zone -- stopping zone



Determine the orange zone -- buffer zone



Determine the red zone -- point of potential damage



Test each zone



Ticket 4 will be something like:

Now that the green zones are determined, use them to:







Find the system center the horizontal gantry on Y & X axes







Allow the user to provide input for shelf dimension generation-- shelf material width: height, width, columns, shelf material width (i.e. wood width-- maybe 1/2" or 3/4"). Have the system generate dimensions of the shelf, including columns.  Then, the cells.  Assume equal shelf cell distribution







Based on that, have the unit the horizontal gantry find the bottom center of each cell.



Next, update the cell dimension funciton or add a second function:  position horizontal gantry from center bottom, to center top, at a given increment (e.g. bottom center zero scan, 1/4" up scan, 1/4" up scan repeat... to top center zero)







provide the shelf dimensions & each collection of each cell's scan locations as output, in a data  object which can be used to reconstruct a 3D shelf diagram in a browser

