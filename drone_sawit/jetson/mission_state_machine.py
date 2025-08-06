# mission_state_machine.py – Mission orchestration using FSM
class MissionStateMachine:
    def __init__(self):
        self.state = "INIT"

    def transition(self, next_state):
        print(f"\U0001F501 {self.state}  {next_state}")
        self.state = next_state

    def run(self):
        while True:
            if self.state == "INIT":
                # Preflight checks
                self.transition("MISSION")
            elif self.state == "MISSION":
                # Main mission loop
                self.transition("COMPLETE")
            elif self.state == "COMPLETE":
                print("Mission Complete")
                break

if __name__ == "__main__":
    MissionStateMachine().run()
