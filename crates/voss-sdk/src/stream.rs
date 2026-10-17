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

/// Open `GET /session/:id/events` and yield typed [`AgentEvent`] values
/// Dropping the returned stream drops the underlying response and closes the TCP
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
            let next_state = EventStreamState::Streaming(std::mem::replace(events, stream::empty().boxed()));
            Some((Ok(event), next_state))
        }
        Some(Err(err)) => Some((Err(err), EventStreamState::Done)),
        None => None,
    }
}

/// Replay after a committed cursor, then stay subscribed across turns. Reconnection
/// belongs to the cache owner, which must commit each envelope before advancing.
pub async fn task_stream(
    client: VossClient, session_id: String, after: u64,
) -> Result<BoxStream<'static, Result<crate::tasks::TaskEvent, VossError>>, VossError> {
    let resp = client.auth(client.inner.get(format!("{}/session/{}/task-events", client.base, session_id)))
        .query(&[("after", after)]).header("Accept", "text/event-stream").send().await?;
    let resp = ok_or_detail(resp).await?;
    Ok(resp.bytes_stream().eventsource().map(move |item| {
        let frame = item.map_err(|e| VossError::Sse(e.to_string()))?;
        let event: crate::tasks::TaskEvent = serde_json::from_str(&frame.data)
            .map_err(|e| VossError::Decode(e.to_string()))?;
        if !event.event.is_object() || event.cursor == 0 || event.v != 1 || event.snapshot.v != 1 || event.snapshot.session_id != session_id
            || event.cursor != event.snapshot.watermark || frame.id.parse::<u64>().ok() != Some(event.cursor) {
            return Err(VossError::Decode("invalid task event identity or cursor".into()));
        }
        Ok(event)
    }).boxed())
}
