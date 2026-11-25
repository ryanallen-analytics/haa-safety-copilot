1. When the model wants a tool, what is the stop_reason, and what fields does a tool_use block have?
The stop_reason is "tool_use", and the tool_use block contains three main fields: id (unique identifier), name (tool being called), and input (arguments passed to the tool). 


2. Why must the assistant’s content go back unchanged in the next request?
The original content must be preserved so Claude can match tool results to the correct tool_use IDs and retain any associated thinking blocks and conversation context without breaking the message sequence. 


3. Where do tool_result blocks go in the next message, and what’s the ordering rule?
They go in a new message with the "user" role, immediately after the assistant's tool-use message, and all tool_result blocks must come before any additional text in that message. 


4. What does is_error: true do, and what makes an error message useful to the model?
Setting is_error: true tells Claude that the tool call failed or was invalid, allowing it to retry or explain the failure; a useful error message clearly identifies what went wrong, such as a missing parameter or an API connection failure. 


5. What does the Define tools page say makes a good tool description?
A good description should be detailed (ideally 3–4 sentences or more), explaining what the tool does, when it should and shouldn't be used, what each parameter means, and any limitations or caveats. 


6. The docs warn that the model sometimes adds arguments the schema doesn’t list. What should your code do when that happens?
My code should validate the arguments against the defined schema and safely ignore or filter out unexpected arguments rather than blindly passing them to the tool or allowing them to cause execution errors.