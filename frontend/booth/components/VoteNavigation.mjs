import { NiceButton, BlueNiceButton } from "./NiceButton.mjs";

function GenericNavigation({ labelInfo=null, labelPreviousButton=null, labelNextButton=null, disabledPreviousButton=false, disabledNextButton=false, hiddenPreviousButton=false, hiddenNextButton=false, onClickPreviousButton=null, onClickNextButton=null }){
  const stylePreviousButton = hiddenPreviousButton ? { display: "none" } : {};
  const styleNextButton = hiddenNextButton ? { display: "none" } : {};
  return e(
    'div',
    {
      className: "vote-navigation-container"
    },
    e(
      'div',
      {
        className: "vote-navigation"
      },
      e(
        'div',
        {
          className: "vote-navigation__info"
        },
        labelInfo
      ),
      e(
        'div',
        {
          className: "vote-navigation__previous-button-container"
        },
        e(
          NiceButton,
          {
            className: "vote-navigation__previous-button",
            label: labelPreviousButton,
            onClick: onClickPreviousButton,
            disabled: disabledPreviousButton,
            style: stylePreviousButton
          }
        )
      ),
      e(
        'div',
        {
          className: "vote-navigation__next-button-container"
        },
        e(
          BlueNiceButton,
          {
            className: "vote-navigation__next-button",
            label: labelNextButton,
            onClick: onClickNextButton,
            disabled: disabledNextButton,
            style: styleNextButton
          }
        )
      )
    )
  );
}

function TranslatableVoteNavigation({ question_index=0, questions_length=1, onClickPreviousButton=null, onClickNextButton=null, t }){
  return GenericNavigation(
    {
      labelInfo: t("questionXofY", {current_question: question_index+1, number_of_questions: questions_length}),
      labelPreviousButton: t("Previous"),
      labelNextButton: t("Next"),
      onClickPreviousButton: question_index == 0 ? null : onClickPreviousButton,
      onClickNextButton: onClickNextButton,
      disabledPreviousButton: question_index == 0 ? true : false,
      hiddenPreviousButton: question_index == 0 ? true : false,
      disabledNextButton: false,
      hiddenNextButton: false
    }
  );
}

const VoteNavigation = ReactI18next.withTranslation()(TranslatableVoteNavigation);

export { VoteNavigation, TranslatableVoteNavigation, GenericNavigation };
export default VoteNavigation;
