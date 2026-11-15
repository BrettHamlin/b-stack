# Full automatic transcript

Source: https://www.youtube.com/watch?v=O_zcc6Xl12g

Raw YouTube automatic captions; technical names are sometimes incorrect. See ANALYSIS.md for slide-checked interpretations.

[0:01](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=1s) [music]

[0:12](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=12s) All right. Um, so again, I'm my name is Potato. Uh, I work on Graphbot at SpaceXsi.

[0:21](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=21s) And can I ask you a quick show of hands?

[0:23](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=23s) How many of you have ever looked at code that somebody else wrote and you thought that's all slop?

[0:31](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=31s) Well, I have too.

[0:35](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=35s) But today, I'm going to convince you that you can turn that slop into gold.

[0:42](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=42s) Uh, and so I did something crazy last month and I shipped 3,000 ploy requests to production. Now, before agents, we

[0:49](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=49s) never really cared about volume. uh except for the outliers.

[0:54](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=54s) And at my previous company, we call these people coding machines. People like Brett Taylor, who famously rewrote all of Google Maps uh in a weekend, just

[1:03](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=63s) an insanely productive engineer. Uh and well, with agents, anyone can now be a coding machine. And my thesis is that

[1:11](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=71s) the job of a software engineer, the meta of being a software engineer is figuring out how to maintain or even improve the

[1:18](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=78s) quality of your code while massively increasing your productivity.

[1:23](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=83s) To get there, some people like to call this a software factory. Uh, but I like to keep it simple and I think of it as all about trust.

[1:32](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=92s) not blind trust, but investing in your agents environment so you can trust that your agents are going to do the right thing. Now, it takes quite a lot of

[1:42](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=102s) effort to get there. Um, and it took me 6 months to get to a point where I could ship thousands of pull requests, a lot

[1:49](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=109s) of them in my sleep, but it's certainly possible and it will take you much less time than I did. So, let's start by

[1:57](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=117s) talking about how we move from a low trust environment to a high trust one.

[2:03](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=123s) So this inverse pyramid is how I think about where to spend time on your agents environment. The first two layers are deterministic.

[2:12](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=132s) So using your code itself. So things like good API design architecture refactoring or using lit rules, type

[2:20](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=140s) systems, compilers or you know different kinds of testing. And you can use both of these layers together to constrain

[2:27](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=147s) what agents can do and force them to do the right thing by default.

[2:32](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=152s) Verification, both runtime and formal, are great tools to layer on to find bugs and check properties and the invariance

[2:40](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=160s) in your system that you want to hold true and also help you check whether or not the agent understood your goals and your intent.

[2:48](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=168s) And then finally, you want to layer with a little bit of pros. So things like rules, skills, agents.mmd, things that require judgment.

[2:59](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=179s) But let's start with your codebase.

[3:01](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=181s) Agents generate their outputs based on their inputs. And so the the quality of the input really matters. And it just so

[3:08](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=188s) happens that your codebase is one of the largest inputs. So whenever you're correcting your agent, think about how

[3:15](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=195s) you can make that a deterministic check instead of adding another line to your rules or your agents.mmd because it's

[3:22](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=202s) far more reproducible when it's in code and it lets you trust it more.

[3:27](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=207s) And the analogy that I like to use is that your codebase is kind of like a garden. You know, code used to arrive a

[3:34](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=214s) few pull requests at a time. And uh I remember going into work in 2024 and reviewing the three pull requests that

[3:42](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=222s) my colleagues wrote colleagues wrote and today that number is more like 300. So uh you know every engineer is now a team

[3:50](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=230s) of hundreds or even thousands of agents and code is arriving so rapidly that it almost feels like a continuous stream

[3:58](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=238s) and it almost feels organic like a living thing.

[4:03](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=243s) And in this analogy, your codebase, the constraints that you impose, the guardrails that you put up are the

[4:10](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=250s) concrete foundations that the new code that your agents write grow around just like uh the building in this picture.

[4:18](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=258s) And so in many ways, the job of being a software engineer is kind of becoming like gardening because code is the biggest input for

[4:26](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=266s) agents. It means that any workarounds, um, anti-atterns, deprecated code, tech,

[4:33](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=273s) it's now likely to be just copied by the next agent since it looks like the established pattern in your codebase.

[4:40](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=280s) And uh, it's like you have some weeds or pests growing in your garden and then they spread everywhere before you know it.

[4:51](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=291s) So you want to make your codebase as pristine as possible so that agents are always copying the good stuff. All right, let's look at some real examples.

[5:00](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=300s) Uh so Dune is a client framework that we created for Grabbot to implement this idea for organic architecture.

[5:08](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=308s) It's not really that interesting technically. Uh you can kind of think of Dune as um kind of like Nex.js for Electron apps. But the interesting part

[5:16](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=316s) of Dune is that it has a lot of constraints and lit rules that we've encoded uh a lot of the lessons that we've learned building desktop applications.

[5:26](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=326s) And one such lesson is that anything that requires nuance to use well often leads to slop. Uh you know your classic

[5:34](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=334s) example is uh you know use effect in React, right? It has its use cases uh but it's often misused. You know some

[5:41](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=341s) people joke that you need a PhD to use use effect. Um and in in other words, it really requires a lot of nuance to use B

[5:50](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=350s) and agents are not good at using it. Um so our solution has been to just ban it in product code and it's really only

[5:58](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=358s) allowed in some places inside of Dune APIs and effectively this problem has now been categorically eliminated and we

[6:07](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=367s) never need to catch that during code review again.

[6:10](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=370s) Another interesting pattern that we use is context through directory structure.

[6:15](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=375s) Uh so one anti-attern that we saw with cursor which is an electron app is that agents would often import main thread

[6:22](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=382s) code into the renderer thread which would cause long tasks and jank.

[6:28](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=388s) So in uh grapot and in dunes we've made this very very conventional. Uh we have these two top level directories

[6:35](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=395s) literally called electron renderer and electron main and imports between them are forbidden or banned by our

[6:42](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=402s) dependency graph analyzer and some lint rules. And again you know these are simple lint rules to set up but it means

[6:49](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=409s) one less thing that we need to review and think about uh you know during code review.

[6:56](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=416s) And then one more surprising thing that I've seen is agents using markdown. So things like documentation, uh, code

[7:04](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=424s) comments, rules or skills, and they use this as a place to write down their justifications for not doing the right thing, or I don't know if you've ever

[7:13](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=433s) seen this, but they'll over rotate on some small correction that you made, and they treat it like a hard rule that can never be broken ever again.

[7:22](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=442s) And here's another example from cursor.

[7:25](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=445s) So agents really loved using imperative timers. So things like set timeout, request animation frame, request idle call back. And they were using these as

[7:33](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=453s) quick fixes because they were really patching over an architecture clash between uh VS Code's imperative style and React's declarative style.

[7:44](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=464s) So our choice of architecture actually made both the client and the agent performance much worse. And if you've

[7:52](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=472s) ever done any performance work in JavaScript, you'll know that when you have tons of timers being rapidly created and destroyed causes a lot of uh

[7:59](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=479s) major garbage collection, which causes a lot of lag and jen. Uh but the worst part is that agents wrote a lot of code

[8:06](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=486s) comments like you can see in red here explaining why this quick fix was justified and before you know it, we had

[8:14](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=494s) timers spreading everywhere and the you know the performance of the app really suffered.

[8:20](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=500s) Now in graphbot uh we learned our lesson there and we decided to just ban 99% of comments uh because they go stale easily

[8:29](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=509s) uh you know humans just really don't bother reading the comment slop anyway and again it gives an agent the an

[8:36](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=516s) escape hatch to justify not doing the right thing because it's hard. Um and the worst part about comments though is

[8:43](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=523s) that they're not enforcable. So what seems well-intentioned, you know, like I'm going to tell the the next agent not to do something, never ends up actually

[8:52](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=532s) being anything that you can trust. So in Grogbot and Dune and in Dune, uh we now have lint rules that give uh good and

[9:01](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=541s) very helpful error messages telling the agent to fix the root cause, the real problem, uh rather than just patch around it.

[9:10](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=550s) And so our general principle is that every time we correct our agents, it turns into one of these deterministic checks or we think about how to categorically eliminate that problem in

[9:19](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=559s) the code through better API design, through better architecture. And if you do this enough times, you'll find that

[9:27](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=567s) you have just less things to look out for in code review. And at some point you realize there's there's nothing left to review and you can just let agents

[9:35](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=575s) merge their most of their own pull requests.

[9:40](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=580s) All right. Uh moving on. Verification is also a really big part of how we make our agents more autonomous and also

[9:48](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=588s) increase our confidence and trust in their work. And our code review process has now really shrunk into looking at verification artifacts instead. So

[9:56](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=596s) things like videos, screenshots, diagrams, formal verification.

[10:02](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=602s) Um, and the most basic example of this is runtime verification. Uh, which is just a fancy way of saying giving your agent a way to run the code for itself

[10:10](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=610s) and use debugging tools that you know, human developers use as well, like the Chrome DevTools protocol. Um, in our runtime verification skills, we have this thing that we call a feature map.

[10:21](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=621s) And that's basically kind of like a site map of all of the features that are available in your application from the user's point of view. And so with this,

[10:30](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=630s) agents don't need to guess when you say, you know, the thingy in the left sidebar. It gives you some shared vocabulary.

[10:37](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=637s) And we also make use of custom CLIs inside these skills so that uh agents can reuse the the CLI and the driver

[10:45](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=645s) every time which cuts down on token usage and is also testable.

[10:50](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=650s) Um and then recently we've also started looking at formal verification. Uh so we now use TA plus to do some model checking of major user flows such as uh

[10:59](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=659s) notifications across multiple devices and platforms. Uh we use a lean as well for proving certain algorithms. Uh for example, we have our own we wrote our

[11:08](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=668s) own custom virtualization library and we use lean there to check that we don't have you know flickering or jittering problems. Um and we're still experimenting with this approach.

[11:18](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=678s) Overall it seems very promising. Uh we've already found quite a few bugs uh with formal verification.

[11:25](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=685s) Um but it's certainly not a silver bullet and we're treating it as another tool, another layer in our agents uh environment.

[11:35](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=695s) Uh and then this is a very fast video but uh another thing that we just started looking at is property based testing as well for UIs. Uh so we use

[11:44](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=704s) this library called Bombadil. Um and this has also caught a few UI bugs for us already.

[11:51](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=711s) Okay. Okay, so zooming out, I saw this tweet from Cindy and six months ago she she said that she was or she was talking

[11:58](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=718s) about not being able to trust her agents because of subtle bugs that were getting merged.

[12:05](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=725s) And really what was missing for her in being able to trust her agents was the verification process. And now 6 months later, she says that 70% of her daily

[12:13](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=733s) tokens go into verification. And I'd say that that tracks with what I see as well, that most of my token usage goes to verification.

[12:22](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=742s) And if you really look closely at our process, none of these things here are new or novel techniques that we've never had before.

[12:30](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=750s) These are just good software engineering tools, but ones that might have been prohibitively expensive to use before as they were hard to understand or write or

[12:39](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=759s) maintain. But agents drastically cut this cost down. And really, we're entering a golden age of software

[12:46](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=766s) testing and verification because agents let us test everything to a much greater degree than used to be economical.

[12:54](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=774s) And then formal verification can also help you better reason about how your product should work and whether your agents really understand your intent and

[13:01](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=781s) goals. Uh I made this new skill called state chart uh in my plug-in PSAC potato stack uh which helps you visualize state

[13:09](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=789s) machines from uh from the user's point of view. Uh, and it's I find this much easier to review alongside the videos

[13:16](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=796s) and screenshots that we provide. Um, and so that's been great. Sorry for the flashbang. Uh, okay. Now, let's look at

[13:24](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=804s) what the promised land looks like. What do you get in return for all of this, uh, you know, investment?

[13:32](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=812s) So, on the Graphbot team, our velocity is uh, taking off and rapidly increasing. And last month, our team

[13:39](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=819s) shipped a ridiculous 11,000 pull requests to production, which is a wild number. And our pace of releasing the

[13:48](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=828s) client has also increased. And we cut a new stable version about once a day.

[13:54](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=834s) And then the core team is also shipping much more. And we also have uh a lot more casual or drive by contributors who

[14:01](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=841s) don't always have a lot of context uh but they're also contributing. Um, and in October we had about 227 people who contributed at least one pull request.

[14:14](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=854s) So despite this velocity accelerating, you might be thinking to yourself like, isn't this going to be chaos? You know, isn't this going to be a bunch of flop?

[14:21](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=861s) But actually, the number of uh PRs that get reverted has actually gotten lower on a relative basis and it's steady at about half a percent.

[14:30](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=870s) But I think the really interesting thing about this shipping pace and this volume of pull requests is that the performance

[14:38](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=878s) of Grabbot has stayed not just stable but has improved on multiple dimensions compared to when we launched. So startup

[14:45](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=885s) typing, opening new chats, switching chats, all of this has gotten faster and keep in mind Grothbot is still an

[14:53](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=893s) Electron app for now. Uh so there is a ceiling, right? But it's already much faster than many other agent UIs out

[15:01](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=901s) there. And for an Electron app with this high velocity and this many people contributing, I'd say that's pretty good.

[15:11](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=911s) So before you jump into building out a software factory and you know automating everything that you can, whenever you correct your agent, try and do it by

[15:19](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=919s) improving your codebase first. you know, start with a lint rule to prevent new occurrences of anti-atterns and then clean up those uh old patterns as well

[15:28](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=928s) and then make sure that your verification story is really strong.

[15:32](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=932s) A lot of this work is a prerequisite to automation anyway. And if your inner coding loop uh produces slop, then

[15:40](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=940s) automating that loop just produces more slop and you need to throw more and more and more tokens at the problem, which we all know is very expensive.

[15:49](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=949s) And once you've made these investments into you know code into your codebase static analysis runtime informal verification you'll start to find that

[15:57](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=957s) many things become possible with these foundations and that you can really easily build your own factory on top of these foundations

[16:07](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=967s) and when you're ready is a great way to build that uh outer loop. We have tons of connectors, routines that can kick off cursor cloud agents and projects uh

[16:16](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=976s) which let you orchestrate thousands of u hundreds or even thousands of agents.

[16:21](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=981s) And as a quick example, you know, whenever we cut a new release now, Grockbot will automatically spin up a new cursor project for us that will fuzz

[16:28](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=988s) the entire application, the entire build, and it will find bugs uh by running the app and using it like a real user. And then it's going to open fixed

[16:37](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=997s) PRs for each of those bugs that it finds and it's going to automerge it as uh crazy as that sounds. And that's because

[16:44](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=1004s) our code base is good enough that pull requests tend to just be good by default. And most product code that we land no longer really requires deep human review.

[16:56](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=1016s) So when you have solid foundations and good organic architecture, you can turn slop into gold and you can ship with

[17:04](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=1024s) high quality uh high velocity without compromising on quality. My name is Potato, also known as Lauren. Thanks you again for listening to my talk.

[17:14](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=1034s) [applause]

