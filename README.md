UDP Pinger Implementation
I developed this project to demonstrate a comprehensive implementation of a UDP-based client-server communication system, designed to test network latency and reliability. The project is divided into two parts, each highlighting different aspects of UDP communication:

Part 1 - Basic UDP Pinger:

I created a lightweight UDP client and server to simulate a simple ping application.
The client sends ping requests to the server, embedding timestamp information to measure round-trip time (RTT).
The server responds to valid requests, allowing me to explore the low-level mechanisms of UDP, such as packet loss handling and timeouts.
Part 2 - Enhanced UDP Pinger:

I added advanced features to handle unreliable network conditions, including dynamic timeout adjustment and robust packet loss simulation.
I extended the functionality with detailed logging for latency metrics, retransmission counts, and packet delivery statistics.
I optimized client-server interaction to emulate real-world scenarios with varying network conditions.
Technical Highlights:

I implemented the project using Python’s socket library, gaining hands-on experience in socket programming and UDP communication.
I incorporated error handling, timeout mechanisms, and acknowledgment protocols to simulate real-world networking challenges.
I analyzed performance metrics and ensured the system was designed to handle reliability issues common in UDP-based systems.
This project allowed me to deepen my understanding of UDP’s strengths and limitations in network programming while honing my skills in designing efficient, resilient communication systems in constrained environments.
