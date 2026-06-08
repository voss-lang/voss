use eventsource_stream::Eventsource;
use futures_util::stream::{self, BoxStream};
use futures_util::{Stream, StreamExt};

use crate::client::{ok_or_detail, VossClient};
use crate::error::VossError;
use crate::types::events::AgentEvent;

enum EventStreamState {
    Connecting { client: VossClient, url: String },
    Streaming(BoxStream<'static, Result<AgentEvent, VossError>>),
    Done,
}

/// Open `GET /session/:id/events` and yield typed [`AgentEvent`] values.
///
/// Dropping the returned stream drops the underlying response and closes the TCP
/// connection, which is the protocol's turn-cancellation signal. No explicit
/// abort request is needed.
pub fn event_stream(
    client: VossClient,
    session_id: String,
) -> impl Stream<Item = Result<AgentEvent, VossError>> + Send + 'static {
    let url = format!("{}/session/{}/events", client.base, session_id);

    stream::unfold(
        EventStreamState::Connecting { client, url },
        |state| async move {
            match state {
                EventStreamState::Connecting { client, url } => {
                    let resp = match client
                        .auth(client.inner.get(url).header("Accept", "text/event-stream"))
                        .send()
                        .await
                    {
                        Ok(resp) => resp,
                        Err(err) => {
                            return Some((Err(VossError::Http(err)), EventStreamState::Done))
                        }
                    };

                    let resp = match ok_or_detail(resp).await {
                        Ok(resp) => resp,
                        Err(err) => return Some((Err(err), EventStreamState::Done)),
                    };

                    let mut events = resp
                        .bytes_stream()
                        .eventsource()
                        .map(|item| match item {
                            Ok(frame) => serde_json::from_str::<AgentEvent>(&frame.data)
                                .map_err(|err| VossError::Decode(err.to_string())),
                            Err(err) => Err(VossError::Sse(err.to_string())),
                        })
                        .boxed();

                    next_event(&mut events).await
                }
                EventStreamState::Streaming(mut events) => next_event(&mut events).await,
                EventStreamState::Done => None,
            }
        },
    )
}

async fn next_event(
    events: &mut BoxStream<'static, Result<AgentEvent, VossError>>,
) -> Option<(Result<AgentEvent, VossError>, EventStreamState)> {
    match events.next().await {
        Some(Ok(event)) => {
            let done = matches!(event, AgentEvent::SessionIdle(_));
            let next_state = if done {
                EventStreamState::Done
            } else {
                EventStreamState::Streaming(std::mem::replace(events, stream::empty().boxed()))
            };
            Some((Ok(event), next_state))
        }
        Some(Err(err)) => Some((Err(err), EventStreamState::Done)),
        None => None,
    }
}
